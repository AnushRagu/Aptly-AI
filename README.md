# Aptly — AI Interview Coach

A polished, local-first mock interview coach that assesses answer content and observable delivery signals.

## Run locally

```bash
# terminal 1
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend && npm install && npm run dev
```

Open the URL shown by Vite (usually `http://localhost:5173`). The app runs fully in **Demo Mode** without external credentials.

## Optional real AI mode

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in the backend environment. The provider is isolated behind `app/ai/provider.py`; deterministic fallbacks remain available if a provider fails.

## Architecture

- `frontend/`: React + TypeScript + Vite, browser recording, speech synthesis, client-side delivery estimates and report UX.
- `backend/`: FastAPI + Pydantic + SQLAlchemy/SQLite, interview persistence, deterministic analysis services and AI provider abstraction.
- Raw recordings are held in browser memory for the current answer and are never persisted by the demo flow. Session deletion removes the persisted interview data.

## Privacy

Camera and microphone access is only requested after the user starts an answer. Delivery signals are approximate observations, not psychological diagnosis. External AI providers may process submitted transcript data when real AI mode is enabled.
