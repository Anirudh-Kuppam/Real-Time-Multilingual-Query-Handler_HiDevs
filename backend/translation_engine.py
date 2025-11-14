import os
from typing import Optional


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# light dependency free fallback
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0


def translate_local(text: str) -> str:
    """Very small fallback: return the same text or very naive pass-through.
    Replace with HF MBART or Helsinki models for production."""
    # In production, load HF models here. For now, simple identity or very naive attempt.
    return text


# optional OpenAI wrapper
def translate_openai(text: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI key not configured")
    import openai
    openai.api_key = OPENAI_API_KEY
    prompt = (
    "You are a high quality translator. Translate the text below into clear natural English and output ONLY the translation.\n\n"
    f"Text:\n{text}\n\nTranslate into English:"
    )
    resp = openai.ChatCompletion.create(
    model="gpt-4o-mini" if hasattr(openai, 'Model') else "gpt-4o",
    messages=[{"role":"user","content":prompt}],
    temperature=0.0,
    max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()