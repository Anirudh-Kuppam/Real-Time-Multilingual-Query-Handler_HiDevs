import os
import requests
from dotenv import load_dotenv
import streamlit as st

# Local utility imports are attempted lazily in functions so app can still run if modules missing.
load_dotenv()

# Config
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Streamlit page setup
st.set_page_config(page_title="Multilingual Query Handler", layout="wide")
st.title("Real-Time Multilingual Query Handler")
st.markdown(
    "Translate incoming customer queries into English in real-time and optionally generate suggested replies."
)

# ---- Utility functions ----

def detect_language_local(text: str) -> str:
    """Detect language using langdetect if available, otherwise return 'unknown'."""
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        return detect(text)
    except Exception:
        return "unknown"

def call_remote_translate(text: str) -> str:
    """Call remote /translate endpoint on FastAPI backend."""
    try:
        resp = requests.post(f"{BACKEND_URL}/translate", json={"text": text}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("translated_text", "")
    except Exception as e:
        raise RuntimeError(f"Remote translation failed: {e}")

def call_remote_response(translated_text: str, name: str = "") -> str:
    """Call remote /response endpoint on FastAPI backend."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/response", json={"translated_text": translated_text, "name": name}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("reply", "")
    except Exception as e:
        raise RuntimeError(f"Remote response generation failed: {e}")

def translate_local(text: str) -> str:
    """
    Local translation fallback.
    Tries backend.translation_engine.translate_local (if present).
    Otherwise returns the input text so the UI continues to work.
    """
    try:
        # try to import user-provided local translator
        from backend.translation_engine import translate_local as tl
        return tl(text)
    except Exception:
        # no local translator available — return input as fallback
        return text

def generate_local_reply(translated_text: str, name: str = "") -> str:
    """
    Local reply generator fallback — tries backend.response_generator.generate_local_reply,
    then utils.prompts.CANNED_REPLY_TEMPLATE, then a simple template.
    """
    try:
        from backend.response_generator import generate_local_reply as glr
        return glr(translated_text, name)
    except Exception:
        try:
            from utils.prompts import CANNED_REPLY_TEMPLATE
            return CANNED_REPLY_TEMPLATE.format(name=(name or "Customer"), excerpt=translated_text[:120])
        except Exception:
            # last-resort template
            nm = name or "Customer"
            return f"Hi {nm}, thanks for reaching out. We received your message: \"{translated_text[:120]}...\" We'll get back within 24 hours."

def save_evaluation_local(entry: dict):
    """Save evaluation using utils.evaluation.save_evaluation if available, else local file storage."""
    try:
        from utils.evaluation import save_evaluation
        save_evaluation(entry)
    except Exception:
        # fallback: append to data/evaluations_local.json
        import json
        from pathlib import Path
        p = Path("data/evaluations_local.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        data = []
        if p.exists():
            try:
                data = json.loads(p.read_text())
            except Exception:
                data = []
        data.append(entry)
        p.write_text(json.dumps(data, indent=2))

def translate_with_openai(text: str) -> str:
    """Translate using OpenAI if key available. Returns translated text or raises."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not configured.")
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        # Minimal prompt for translation
        prompt = (
            "You are a translator. Translate the following text into clear natural English. "
            "Output ONLY the translation.\n\n"
            f"Text:\n{text}\n\nTranslate into English:"
        )
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini" if hasattr(openai, "Model") else "gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1024,
        )
        translated = resp.choices[0].message.content.strip()
        return translated
    except Exception as e:
        raise RuntimeError(f"OpenAI translation failed: {e}")

def generate_reply_with_openai(translated_text: str, name: str = "", temperature: float = 0.2) -> str:
    """Generate reply using OpenAI (if configured)."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not configured.")
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        prompt = (
            "You are an empathetic customer support agent. Using the message below, write a concise, polite reply "
            "(3-6 sentences). Ask clarifying questions if needed and suggest next steps.\n\n"
            f"Customer message:\n{translated_text}\n\nReply:"
        )
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini" if hasattr(openai, "Model") else "gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=256,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"OpenAI response generation failed: {e}")

# ---- UI elements ----

st.sidebar.header("Settings")
backend_choice = st.sidebar.selectbox("Backend", ["remote (FastAPI)", "local"])
translation_backend = st.sidebar.selectbox("Translation backend", ["auto", "openai", "local"])
response_mode = st.sidebar.selectbox("Default response mode", ["AI-generated (if available)", "Canned (template)"])
ai_temperature = st.sidebar.slider("AI response temperature", 0.0, 1.0, 0.2, 0.05)

st.sidebar.markdown("---")
st.sidebar.write("Backend URL:")
st.sidebar.write(BACKEND_URL)
if OPENAI_API_KEY:
    st.sidebar.success("OpenAI key configured")
else:
    st.sidebar.info("No OpenAI key found; OpenAI features disabled")

st.subheader("Incoming Customer Query")

with st.form("incoming_form"):
    customer_name = st.text_input("Customer name (optional)")
    incoming_text = st.text_area("Paste the customer's message here", height=180)
    want_generate = st.checkbox("Generate suggested response", value=True)
    submit_btn = st.form_submit_button("Translate & Process")

# Initialize safe defaults so we never reference undefined variables
translated = ""
suggested = ""
detected_lang = "unknown"

# Processing on submit
if submit_btn:
    if not incoming_text.strip():
        st.warning("Please paste a message to translate.")
    else:
        st.markdown("### Processing")
        # 1) Language detection
        detected_lang = detect_language_local(incoming_text)
        st.write(f"**Detected language code:** `{detected_lang}`")

        # 2) Choose translation path: remote FastAPI -> OpenAI -> local fallback
        translate_error = None
        try:
            if backend_choice.startswith("remote"):
                # prefer remote translation
                try:
                    translated = call_remote_translate(incoming_text)
                except Exception as e_remote:
                    # If remote fails, optionally try OpenAI or local
                    translate_error = f"Remote translation failed: {e_remote}"
                    if translation_backend == "openai" and OPENAI_API_KEY:
                        translated = translate_with_openai(incoming_text)
                    elif translation_backend == "local":
                        translated = translate_local(incoming_text)
                    else:
                        # try openai automatically if key present
                        if OPENAI_API_KEY:
                            translated = translate_with_openai(incoming_text)
                        else:
                            translated = translate_local(incoming_text)
            else:
                # local-only
                if translation_backend == "openai" and OPENAI_API_KEY:
                    translated = translate_with_openai(incoming_text)
                else:
                    translated = translate_local(incoming_text)
        except Exception as e:
            translate_error = str(e)
            translated = ""

        if translate_error:
            st.error(translate_error)

        if translated:
            st.markdown("### Translated to English")
            st.success(translated)

            # 3) Generate suggested reply if requested
            if want_generate:
                gen_error = None
                try:
                    if response_mode.startswith("AI") or response_mode == "AI-generated (if available)":
                        # Prefer remote response, then OpenAI, then local canned
                        if backend_choice.startswith("remote"):
                            try:
                                suggested = call_remote_response(translated, customer_name)
                            except Exception:
                                # remote failed -> fallback to OpenAI/local
                                if OPENAI_API_KEY:
                                    suggested = generate_reply_with_openai(translated, customer_name, ai_temperature)
                                else:
                                    suggested = generate_local_reply(translated, customer_name)
                        else:
                            # local only
                            if translation_backend == "openai" and OPENAI_API_KEY:
                                suggested = generate_reply_with_openai(translated, customer_name, ai_temperature)
                            else:
                                suggested = generate_local_reply(translated, customer_name)
                    else:
                        # canned template
                        suggested = generate_local_reply(translated, customer_name)
                except Exception as e:
                    gen_error = str(e)
                    suggested = ""

                if gen_error:
                    st.error(gen_error)

                if suggested:
                    st.markdown("### Suggested Reply")
                    st.info(suggested)
                else:
                    st.warning("No suggested reply produced.")
        else:
            st.warning("No translation was produced.")

        # 4) Evaluation form (save rating + comments locally)
        st.markdown("---")
        st.subheader("Quick Evaluation")
        rating = st.slider("Rate translation accuracy (1 = poor, 5 = perfect)", 1, 5, 4)
        comments = st.text_area("Comments (optional)")
        if st.button("Save evaluation"):
            entry = {
                "input": incoming_text,
                "detected_language": detected_lang,
                "translated": translated,
                "suggested": suggested,
                "rating": int(rating),
                "comments": comments,
            }
            try:
                save_evaluation_local(entry)
                st.success("Evaluation saved.")
            except Exception as e:
                st.error(f"Failed to save evaluation: {e}")

# Footer / help
st.markdown("---")
st.markdown(
    "Tips: 1) Run `uvicorn backend.server:app --reload --port 8000` to enable remote backend.  "
    "2) Add `OPENAI_API_KEY` to `.env` to use OpenAI.  "
    "3) Replace `translate_local` with a Hugging Face model for better local translations."
)