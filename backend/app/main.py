import json
import uuid
import os
import tempfile

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import Interview
from .schemas import CreateInterview, AnswerRequest
from .analysis import filler_analysis, pacing, pauses, content_analysis
from .ai.fallback_provider import FallbackProvider
from .ai.gemini_provider import GeminiProvider
from .ai.transcription import transcribe_audio


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Aptly API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

provider = (
    GeminiProvider(os.getenv("GEMINI_API_KEY"))
    if os.getenv("GEMINI_API_KEY")
    else FallbackProvider()
)

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "live" if os.getenv("GEMINI_API_KEY") else "demo"
    }

@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    temp_path = None

    try:
        audio_data = await file.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file"
            )

        suffix = ".webm"

        if file.filename:
            _, ext = os.path.splitext(file.filename)
            if ext:
                suffix = ext

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp:
            temp.write(audio_data)
            temp_path = temp.name

        result = transcribe_audio(temp_path)        
        return {
            "text": result.get("text", ""),
            "words": result.get("words", [])
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(f"[transcribe] Error: {exc}")

        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(exc)}"
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.post("/api/interviews/create")
def create(
    payload: CreateInterview,
    db: Session = Depends(db_session)
):
    try:
        profile = provider.profile(
            payload.title,
            payload.job_description
        )

        questions = provider.generate_questions(
            payload.title,
            payload.job_description,
            payload.interview_type,
            payload.difficulty
        )

    except Exception as e:
        print(f"[AI fallback] {e}")

        profile = {
            "role": payload.title,
            "seniority": "Early-to-mid career",
            "skills": [
                "Problem solving",
                "Communication",
                "Technical knowledge"
            ],
            "technologies": [],
            "responsibilities": [
                "Deliver technical solutions",
                "Collaborate with team members"
            ],
            "behavioral_competencies": [
                "Ownership",
                "Adaptability",
                "Communication"
            ],
            "likely_topics": [
                "Technical fundamentals",
                "Projects",
                "Problem solving",
                "Behavioral questions"
            ]
        }

        questions = {
            "questions": [
                {
                    "question": f"Tell me about yourself and your experience relevant to the {payload.title} role.",
                    "type": "behavioral"
                },
                {
                    "question": "Tell me about a challenging technical problem you solved.",
                    "type": "technical"
                },
                {
                    "question": "Explain one of your projects and the technical decisions you made.",
                    "type": "technical"
                },
                {
                    "question": "Describe a situation where you had to learn something quickly.",
                    "type": "behavioral"
                },
                {
                    "question": "Why are you interested in this role?",
                    "type": "behavioral"
                }
            ]
        }

    item = Interview(
        id=str(uuid.uuid4()),
        title=payload.title,
        company=payload.company,
        interview_type=payload.interview_type,
        difficulty=payload.difficulty,
        job_description=payload.job_description,
        profile_json=json.dumps(profile)
    )

    db.add(item)
    db.commit()

    return {
        "id": item.id,
        "profile": profile,
        "questions": questions["questions"],
        "mode": "live" if os.getenv("GEMINI_API_KEY") else "demo"
    }


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    temp_path = None

    try:
        suffix = ".webm"

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp:

            content = await file.read()
            temp.write(content)
            temp_path = temp.name

        result = transcribe_audio(temp_path)

        return {
            "text": result.get("text", ""),
            "words": result.get("words", [])
        }

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/interviews/{interview_id}/answer")
def answer(
    interview_id: str,
    payload: AnswerRequest,
    db: Session = Depends(db_session)
):
    item = db.get(Interview, interview_id)

    if not item:
        raise HTTPException(
            404,
            "Interview not found"
        )

    filler_data = filler_analysis(
    payload.transcript,
    [
        word.model_dump()
        for word in payload.words
    ]
)

    pacing_data = pacing(
        payload.transcript,
        payload.duration_seconds
    )

    pause_data = pauses(
        payload.transcript,
        payload.duration_seconds,
        [
            word.model_dump()
            for word in payload.words
        ]
    )

    delivery = {
        "fillers": filler_data,
        "pacing": pacing_data,
        "pauses": pause_data,
        "eye_contact": (
            payload.eye_contact
            if payload.eye_contact is not None
            else 0
        ),
        "voice_energy": "stable",
    }

    try:
        content = provider.evaluate_answer(
            item.title,
            payload.question,
            payload.question_type,
            payload.transcript
        )

    except Exception as e:
        print(f"[AI evaluation fallback] {e}")

        content = content_analysis(
            payload.question,
            payload.question_type,
            payload.transcript
        )

    # Normalize content scores for the frontend
    content["technical_depth"] = content.get(
        "technical_depth",
        content.get("depth", 0)
    )

    content["overall_score"] = round(
        (
            content.get("relevance", 0) +
            content.get("structure", 0) +
            content.get("technical_depth", 0)
        ) / 3
)

    try:
        follow_up = provider.follow_up(
            item.title,
            payload.transcript,
            payload.question_type
        )
    except Exception as e:
        print(f"[AI follow-up fallback] {e}")

        follow_up = (
            "Can you explain your reasoning in more detail "
            "and describe how you would approach this in a real project?"
        )

    answers = json.loads(item.answers_json)

    answers.append({
        "question": payload.question,
        "question_type": payload.question_type,
        "transcript": payload.transcript,
        "duration": payload.duration_seconds,
        "delivery": delivery,
        "content": content
    })

    item.answers_json = json.dumps(answers)

    db.commit()

    return {
        "delivery": delivery,
        "content": content,
        "follow_up": follow_up
    }


@app.get("/api/interviews/{interview_id}/report")
def report(
    interview_id: str,
    db: Session = Depends(db_session)
):
    item = db.get(Interview, interview_id)

    if not item:
        raise HTTPException(
            404,
            "Interview not found"
        )

    answers = json.loads(
        item.answers_json
    )

    return {
        "id": item.id,
        "title": item.title,
        "answers": answers,
        "profile": json.loads(
            item.profile_json
        )
    }


@app.get("/api/interviews/history")
def history(
    db: Session = Depends(db_session)
):
    return [
        {
            "id": x.id,
            "title": x.title,
            "created_at": x.created_at
        }
        for x in db.query(Interview)
        .order_by(Interview.created_at.desc())
        .limit(12)
    ]


@app.delete("/api/interviews/{interview_id}")
def delete(
    interview_id: str,
    db: Session = Depends(db_session)
):
    item = db.get(Interview, interview_id)

    if not item:
        raise HTTPException(
            404,
            "Interview not found"
        )

    db.delete(item)
    db.commit()

    return {
        "deleted": True
    }