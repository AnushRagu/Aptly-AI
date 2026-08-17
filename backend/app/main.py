import json, uuid
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import Interview
from .schemas import CreateInterview, AnswerRequest
from .analysis import filler_analysis, pacing, pauses, content_analysis
from .ai.fallback_provider import FallbackProvider
from .ai.openai_provider import OpenAICompatibleProvider

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Aptly API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
provider = OpenAICompatibleProvider() if os.getenv("OPENAI_API_KEY") else FallbackProvider()

def db_session():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/api/health")
def health(): return {"status": "ok", "mode": "live" if os.getenv("OPENAI_API_KEY") else "demo"}

@app.post("/api/interviews/create")
def create(payload: CreateInterview, db: Session = Depends(db_session)):
    profile = provider.profile(payload.title, payload.job_description)
    item = Interview(id=str(uuid.uuid4()), title=payload.title, company=payload.company, interview_type=payload.interview_type, difficulty=payload.difficulty, job_description=payload.job_description, profile_json=json.dumps(profile))
    db.add(item); db.commit()
    return {"id": item.id, "profile": profile, "mode": "demo"}

@app.post("/api/interviews/{interview_id}/answer")
def answer(interview_id: str, payload: AnswerRequest, db: Session = Depends(db_session)):
    item = db.get(Interview, interview_id)
    if not item: raise HTTPException(404, "Interview not found")
    delivery = {"fillers": filler_analysis(payload.transcript, payload.duration_seconds), "pacing": pacing(payload.transcript, payload.duration_seconds), "pauses": pauses(payload.transcript, payload.duration_seconds), "eye_contact": payload.eye_contact if payload.eye_contact is not None else 76, "voice_energy": "stable"}
    content = content_analysis(payload.question, payload.question_type, payload.transcript)
    follow_up = provider.follow_up(item.title, payload.transcript, payload.question_type)
    answers = json.loads(item.answers_json); answers.append({"question": payload.question, "question_type": payload.question_type, "transcript": payload.transcript, "duration": payload.duration_seconds, "delivery": delivery, "content": content}); item.answers_json = json.dumps(answers); db.commit()
    return {"delivery": delivery, "content": content, "follow_up": follow_up}

@app.get("/api/interviews/{interview_id}/report")
def report(interview_id: str, db: Session = Depends(db_session)):
    item = db.get(Interview, interview_id)
    if not item: raise HTTPException(404, "Interview not found")
    answers = json.loads(item.answers_json)
    return {"id": item.id, "title": item.title, "answers": answers, "profile": json.loads(item.profile_json)}

@app.get("/api/interviews/history")
def history(db: Session = Depends(db_session)):
    return [{"id": x.id, "title": x.title, "created_at": x.created_at} for x in db.query(Interview).order_by(Interview.created_at.desc()).limit(12)]

@app.delete("/api/interviews/{interview_id}")
def delete(interview_id: str, db: Session = Depends(db_session)):
    item = db.get(Interview, interview_id)
    if not item: raise HTTPException(404, "Interview not found")
    db.delete(item); db.commit(); return {"deleted": True}
