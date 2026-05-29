# 🔥 LOAD ENV FIRST (VERY IMPORTANT)
from dotenv import load_dotenv
import os

load_dotenv()

# ---------------- IMPORTS ----------------
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import cv2
import numpy as np
import mediapipe as mp
import uuid
import subprocess
import random
import torch
import soundfile as sf
import json

from faster_whisper import WhisperModel
from silero_vad import load_silero_vad

from openai import OpenAI

from database import engine, Base, get_db
from models.question import Question
from routes.answer_routes import router as answer_router
from routes.memberdashboard_routes import router as memberdashboard_router
from routes.auth_routes import router as auth_router
from core.session_store import INTERVIEW_SESSIONS

from models.model import Candidate, Panel, PanelMember, Interview, User

from typing import Optional, List
from routes import auth_routes as auth

from pydantic import BaseModel
from datetime import datetime

# ---------------- APP INIT ----------------
app = FastAPI()

Base.metadata.create_all(bind=engine)

# 🔥 FFmpeg path
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg-8.1-essentials_build\bin"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"

# 🔥 Recording path
RECORDING_BASE_PATH = "C:/Users/saipa/OneDrive/Desktop/Recordings"
os.makedirs(RECORDING_BASE_PATH, exist_ok=True)

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ROUTERS ----------------
app.include_router(answer_router)
app.include_router(memberdashboard_router)
app.include_router(auth_router)

# ---------------- MODELS ----------------
# model = WhisperModel(
#     "tiny",
#     device="cpu",          # 🔥 FORCE CPU
#     compute_type="int8"
# )

# vad_model = load_silero_vad()

model = None
vad_model = None

def get_models():
    global model, vad_model

    if model is None:
        print("🚀 Loading Whisper model...")
        model = WhisperModel("small", device="cpu", compute_type="int8")

    if vad_model is None:
        print("🚀 Loading VAD model...")
        vad_model = load_silero_vad()

    return model, vad_model


mp_face_detection = mp.solutions.face_detection

# ---------------- OPENAI CLIENT ----------------
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=api_key)

print("✅ API KEY LOADED SUCCESSFULLY")

# ---------------- HELPER ----------------
def is_repetitive(text: str) -> bool:
    words = text.lower().split()
    if len(words) < 6:
        return False
    unique_words = set(words)
    ratio = 1 - (len(unique_words) / len(words))
    return ratio > 0.6

# ---------------- START INTERVIEW ----------------
@app.post("/start-interview")
def start_interview(db: Session = Depends(get_db)):

    questions = db.query(Question).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")

    random.shuffle(questions)

    interview_id = str(uuid.uuid4())

    INTERVIEW_SESSIONS[interview_id] = {
        "questions": [q.id for q in questions],
        "current_index": 0,
        "completed": False
    }

    return {"interview_id": interview_id}

# ---------------- NEXT QUESTION ----------------
@app.get("/next-question/{interview_id}")
def get_next_question(interview_id: int, db: Session = Depends(get_db)):

    # 🔥 convert to string (since dict keys are string)
    interview_key = str(interview_id)

    # ---------------- INIT SESSION IF NOT EXISTS ----------------
    if interview_key not in INTERVIEW_SESSIONS:

        questions = db.query(Question).all()

        if not questions:
            raise HTTPException(status_code=404, detail="No questions found")

        random.shuffle(questions)

        INTERVIEW_SESSIONS[interview_key] = {
            "questions": [q.id for q in questions],
            "current_index": 0,
            "completed": False
        }

    session = INTERVIEW_SESSIONS[interview_key]

    # ---------------- CHECK COMPLETION ----------------
    if session["current_index"] >= len(session["questions"]):
        session["completed"] = True
        return {"message": "Interview completed"}

    # ---------------- FETCH QUESTION ----------------
    question_id = session["questions"][session["current_index"]]

    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # ---------------- INCREMENT INDEX ----------------
    session["current_index"] += 1

    return question

# ---------------- SAVE FULL VIDEO ----------------
@app.post("/save-video/{interview_id}")
async def save_video(
    interview_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    try:
        # 🔥 Ensure directory exists
        os.makedirs(RECORDING_BASE_PATH, exist_ok=True)

        # 🔥 Build path
        video_path = os.path.join(RECORDING_BASE_PATH, f"{interview_id}.webm")

        # 🔥 Normalize (OS safe)
        video_path = os.path.normpath(video_path)

        # 🔥 Save file
        contents = await file.read()

        with open(video_path, "wb") as f:
            f.write(contents)

        # ---------------- FETCH INTERVIEW ----------------
        interview = db.query(Interview).filter(Interview.id == interview_id).first()

        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        # 🔥 Clean path for DB (forward slashes)
        db_path = video_path.replace("\\", "/")

        # ---------------- UPDATE INTERVIEW ----------------
        interview.video_path = db_path
        interview.status = "Completed"

        # ---------------- UPDATE CANDIDATE ----------------
        candidate = db.query(Candidate).filter(
            Candidate.id == interview.candidate_id
        ).first()

        if candidate:
            candidate.video_path = db_path

        db.commit()

        return {
            "message": "Video saved and updated successfully",
            "video_path": db_path
        }

    except Exception as e:
        print("❌ SAVE VIDEO ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))
    

# ---------------- SPEECH TO TEXT ----------------
@app.post("/speech-to-text")
async def speech_to_text(file: UploadFile = File(...)):

    video_path = None
    audio_path = None

    try:
        uid = uuid.uuid4()
        video_path = f"temp_{uid}.webm"
        audio_path = f"temp_{uid}.wav"

        # ---------------- SAVE FILE ----------------
        with open(video_path, "wb") as f:
            f.write(await file.read())

        # Ignore very small chunks (silence / noise)
        if os.path.getsize(video_path) < 2000:
            return {"text": None}   # 🔥 IMPORTANT

        # ---------------- CONVERT AUDIO ----------------
        result = subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            print("❌ FFmpeg Error:", result.stderr.decode())
            return {"text": None}

        # Check audio file
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 5000:
            return {"text": None}

        # ---------------- LOAD MODEL (LAZY) ----------------
        model, _ = get_models()

        # ---------------- TRANSCRIBE ----------------
        segments, info = model.transcribe(
            audio_path,
            beam_size=1,
            vad_filter=False,   # 🔥 disable for stability
            language="en"
        )

        text = " ".join([seg.text for seg in segments]).strip()

        # ---------------- DEBUG ----------------
        print("🧠 RAW TEXT:", text)

        # ---------------- CLEAN TEXT ----------------
        bad_phrases = ["i'm sorry", "thank you", "sorry", "thanks"]

        if any(p in text.lower() for p in bad_phrases):
            text = ""

        if is_repetitive(text):
            text = ""

        # 🔥 IMPORTANT: Don't kill short valid answers
        if len(text.strip()) < 2:
            text = ""

        # 🔥 KEY FIX: do NOT overwrite with empty
        if not text:
            return {"text": None}

        return {"text": text}

    except Exception as e:
        print("❌ Error:", e)
        return {"text": None}

    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

@app.post("/ask-ai")
async def ask_ai(question: str, answer: str):

    try:
        prompt = f"""
You are an expert technical assistant.

A candidate answered a question, but the speech-to-text output has errors.

Your job:
- Fix incorrect words (like "R pictures" → "microservices")
- Correct grammar
- Remove repetition
- Keep the original meaning
- Do NOT add new information

QUESTION:
{question}

RAW ANSWER:
{answer}

Return ONLY the corrected sentence.
"""

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You fix speech recognition errors using context."},
                {"role": "user", "content": prompt}
            ]
        )

        corrected = response.choices[0].message.content.strip()

        return {
            "corrected_text": corrected
        }

    except Exception as e:
        print("❌ ChatGPT Error:", e)
        return {"corrected_text": answer}
       

@app.post("/speech-to-ai")
async def speech_to_ai(file: UploadFile = File(...)):

    result = await speech_to_text(file)

    text = result.get("text", "")

    if not text:
        return {
            "text": "",
            "response": ""
        }

    try:
        ai_res = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI interviewer."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        return {
            "text": text,
            "response": ai_res.choices[0].message.content
        }

    except Exception as e:
        print("❌ AI Error:", e)
        return {
            "text": text,
            "response": ""
        }
    

# ---------------- FACE DETECTION ----------------
@app.post("/detect-face")
async def detect_face(file: UploadFile = File(...)):

    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        return {"faces": 0}

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp_face_detection.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.5
    ) as fd:
        results = fd.process(rgb)

    faces = len(results.detections) if results.detections else 0

    return {"faces": faces}

app.include_router(auth.router, prefix="/api/auth")

# Load AI models
# whisper_model = whisper.load_model("medium")
# model = WhisperModel("medium")
mp_face_detection = mp.solutions.face_detection

# ============================================
# PYDANTIC MODELS
# ============================================

class InterviewRequest(BaseModel):
    applied_role: str
    interview_date: str
    start_time: str
    end_time: str
    
    # Panel - either existing or new
    panel_id: Optional[int] = None
    panel_name: Optional[str] = None
    chairman_user_id: Optional[int] = None
    member_user_ids: Optional[List[int]] = None
    
    # Student details
    student_full_name: str
    student_father_mother_name: Optional[str] = None
    student_dob: Optional[str] = None
    student_gender: Optional[str] = None
    student_category: Optional[str] = None
    student_mobile: Optional[str] = None
    student_alt_mobile: Optional[str] = None
    student_email: Optional[str] = None
    student_current_address: Optional[str] = None
    student_permanent_address: Optional[str] = None
    student_course_program: Optional[str] = None
    student_department_branch: Optional[str] = None
    student_university: Optional[str] = None
    student_enrollment_no: Optional[str] = None
    student_academic_year: Optional[str] = None
    student_cgpa: Optional[str] = None
    student_skills: Optional[str] = None
    student_certifications: Optional[str] = None
    student_projects: Optional[str] = None
    student_experience: Optional[str] = None
    student_strengths: Optional[str] = None
    student_weaknesses: Optional[str] = None
    student_career_objective: Optional[str] = None
    student_declaration: bool

# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_interview_id():
    year = datetime.now().year
    num = random.randint(1000, 9999)
    return f"IVW-{year}-{num}"

# ============================================
# ROUTES
# ============================================

@app.get("/")
def root():
    return {"message": "Interview Scheduling API", "status": "running"}

# ============================================
# USER ROUTES (for panel members)
# ============================================

@app.get("/api/users/interviewers")
def get_interviewers(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "designation": user.designation,
            "role": user.role
        })
    return {"success": True, "data": result}

# ============================================
# PANEL ROUTES
# ============================================

@app.get("/api/panels")
def get_panels(db: Session = Depends(get_db)):
    panels = db.query(Panel).all()
    result = []
    for panel in panels:
        members = db.query(PanelMember).filter(PanelMember.panel_id == panel.id).all()
        result.append({
            "id": panel.id,
            "panel_name": panel.panel_name,
            "member_count": len(members),
            "created_at": panel.created_at
        })
    return {"success": True, "data": result}

# ============================================
# INTERVIEW ROUTES
# ============================================

@app.post("/api/schedule-interview")
def schedule_interview(data: InterviewRequest, db: Session = Depends(get_db)):
    try:
        # Generate interview ID
        interview_id = generate_interview_id()
        
        # 1. Create candidate
        candidate = Candidate(
            name=data.student_full_name,
            email=data.student_email,
            phone=data.student_mobile,
            interview_id=interview_id,
            student_father_mother_name=data.student_father_mother_name,
            student_dob=data.student_dob,
            student_gender=data.student_gender,
            student_category=data.student_category,
            student_alt_mobile=data.student_alt_mobile,
            student_current_address=data.student_current_address,
            student_permanent_address=data.student_permanent_address,
            student_course_program=data.student_course_program,
            student_department_branch=data.student_department_branch,
            student_university=data.student_university,
            student_enrollment_no=data.student_enrollment_no,
            student_academic_year=data.student_academic_year,
            student_cgpa=data.student_cgpa,
            student_skills=data.student_skills,
            student_certifications=data.student_certifications,
            student_projects=data.student_projects,
            student_experience=data.student_experience,
            student_strengths=data.student_strengths,
            student_weaknesses=data.student_weaknesses,
            student_career_objective=data.student_career_objective,
            student_declaration=data.student_declaration
        )
        
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        
        # 2. Handle panel (existing or new)
        if data.panel_id:
            # Use existing panel
            panel = db.query(Panel).filter(Panel.id == data.panel_id).first()
            if not panel:
                raise HTTPException(status_code=404, detail="Panel not found")
        else:
            # Create new panel
            panel = Panel(
                panel_name=data.panel_name or f"{data.applied_role} Panel",
                created_by=1  # You might want to get this from auth
            )
            db.add(panel)
            db.commit()
            db.refresh(panel)
            
            # Add panel members
            if data.member_user_ids:
                for user_id in data.member_user_ids:
                    role = "chairman" if user_id == data.chairman_user_id else "member"
                    panel_member = PanelMember(
                        panel_id=panel.id,
                        user_id=user_id,
                        role=role
                    )
                    db.add(panel_member)
                db.commit()
        
        # 3. Create interview
        interview = Interview(
            candidate_id=candidate.id,
            panel_id=panel.id,
            scheduled_at=f"{data.interview_date} {data.start_time}",
            status="Scheduled",
            created_by=1
        )
        
        db.add(interview)
        db.commit()
        db.refresh(interview)
        
        return {
            "success": True,
            "message": "Interview scheduled successfully",
            "interview_id": interview_id,
            "data": {
                "candidate_id": candidate.id,
                "panel_id": panel.id,
                "interview_id": interview_id
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interviews")
def get_all_interviews(db: Session = Depends(get_db)):
    interviews = db.query(Interview).all()
    result = []
    
    for interview in interviews:
        candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
        panel = db.query(Panel).filter(Panel.id == interview.panel_id).first()
        
        result.append({
            "id": interview.id,
            "interview_id": candidate.interview_id if candidate else None,
            "candidate_name": candidate.name if candidate else None,
            "email": candidate.email if candidate else None,
            "phone": candidate.phone if candidate else None,
            "panel_name": panel.panel_name if panel else None,
            "scheduled_at": interview.scheduled_at,
            "status": interview.status,
            "created_at": interview.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return {"success": True, "data": result}

@app.get("/api/interviews/{id}")
def get_interview(id: int, db: Session = Depends(get_db)):

    interview = db.query(Interview).filter(Interview.id == id).first()

    if not interview:
        return {"success": False, "message": "Interview not found"}

    candidate = interview.candidate
    panel = interview.panel
    members = db.query(PanelMember).filter(
        PanelMember.panel_id == panel.id
    ).all()

    return {
        "success": True,
        "data": {
            "candidate": candidate,
            "interview": interview,
            "panel": panel,
            "members": members
        }
    }


@app.delete("/api/interviews/{interview_id}")
def delete_interview(interview_id: str, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.interview_id == interview_id).first()
    if not candidate:
        return {"success": False, "message": "Interview not found"}
    
    interview = db.query(Interview).filter(Interview.candidate_id == candidate.id).first()
    
    db.delete(interview)
    db.delete(candidate)
    db.commit()
    
    return {"success": True, "message": "Interview deleted successfully"}

# ============================================
# FILE UPLOAD ROUTES
# ============================================

@app.post("/api/candidates/{candidate_id}/upload")
async def upload_candidate_file(
    candidate_id: int,
    file_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Save file logic here
    file_location = f"uploads/{candidate_id}_{file_type}_{file.filename}"
    os.makedirs(os.path.dirname(file_location), exist_ok=True)
    
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Update candidate record with filename
    if file_type == "photo":
        candidate.photo_filename = file.filename
    elif file_type == "resume":
        candidate.resume_filename = file.filename
    elif file_type == "idproof":
        candidate.idproof_filename = file.filename
    elif file_type == "certificates":
        candidate.certificates_filename = file.filename
    
    db.commit()
    
    return {"success": True, "message": "File uploaded successfully"}


@app.get("/interview/{interview_id}")
def get_interview(interview_id: int, db: Session = Depends(get_db)):

    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return {
        "id": interview.id,

        # 🔥 candidate info
        "candidate": {
            "id": interview.candidate.id,
            "name": interview.candidate.name,
            "email": interview.candidate.email,
            "video_path": interview.candidate.video_path
        } if interview.candidate else None,

        # 🔥 panel info
        "panel": {
            "id": interview.panel.id,
            "panel_name": interview.panel.panel_name
        } if interview.panel else None,

        # 🔥 main fields
        "candidate_id": interview.candidate_id,
        "panel_id": interview.panel_id,
        "scheduled_at": interview.scheduled_at,
        "status": interview.status,
        "video_path": interview.video_path
    }   