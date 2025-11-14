import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
from utils.prompts import CANNED_REPLY_TEMPLATE


def generate_local_reply(translated_text: str, name: str = "") -> str:
    # Short, template-based reply
    return CANNED_REPLY_TEMPLATE.format(name=(name or "Customer"), excerpt=translated_text[:120])


def generate_openai_reply(translated_text: str, name: str = "", temperature: float = 0.2) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI key not configured")
    import openai
    openai.api_key = OPENAI_API_KEY
    prompt = (
    "You are an empathetic customer support agent. Using the message below, write a concise and polite reply (3-6 sentences).\n\n"
    f"Customer message:\n{translated_text}\n\nReply:"
    )
    resp = openai.ChatCompletion.create(
    model="gpt-4o-mini" if hasattr(openai, 'Model') else "gpt-4o",
    messages=[{"role":"user","content":prompt}],
    temperature=temperature,
    max_tokens=256,
    )
    return resp.choices[0].message.content.strip()