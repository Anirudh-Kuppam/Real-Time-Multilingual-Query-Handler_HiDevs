# Multilingual Query Handler


Minimal starter project for a multilingual query translation and response generator.


## Quick start


1. Create `.env` with `OPENAI_API_KEY` if using OpenAI.
2. Install dependencies: `pip install -r requirements.txt`
3. Start backend (optional): `uvicorn backend.server:app --reload --port 8000`
4. Start UI: `streamlit run app.py`


## Notes
- `backend/translation_engine.py` and `backend/response_generator.py` include OpenAI wrappers — configure the key to enable them.
- For production replace `translate_local` with HF model implementations (see `transformers` docs).