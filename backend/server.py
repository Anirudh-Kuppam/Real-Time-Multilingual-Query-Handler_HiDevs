from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.translation_engine import translate_local, translate_openai
from backend.response_generator import generate_openai_reply


app = FastAPI()


class TranslateRequest(BaseModel):
    text: str


class ResponseRequest(BaseModel):
    translated_text: str
    name: str = ""


@app.post('/translate')
async def translate(req: TranslateRequest):
    try:
    # prefer OpenAI if configured, else local
        translated = translate_openai(req.text)
    except Exception:
        translated = translate_local(req.text)
    return {"translated_text": translated}


@app.post('/response')
async def response(req: ResponseRequest):
    try:
        reply = generate_openai_reply(req.translated_text, req.name)
    except Exception:
# fallback canned
        from utils.prompts import CANNED_REPLY_TEMPLATE
        reply = CANNED_REPLY_TEMPLATE.format(name=(req.name or "Customer"), excerpt=req.translated_text[:120])
    return {"reply": reply}