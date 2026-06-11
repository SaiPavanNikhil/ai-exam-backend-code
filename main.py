# 🔥 LOAD ENV FIRST (VERY IMPORTANT)
from dotenv import load_dotenv
import os

from sqlalchemy import func

from models.SelfAssessmentResult import SelfAssessmentResult
from models.SelfAssessmentAnswer import SelfAssessmentAnswer
from schemas import save_answer_request
from schemas.grading_schema import GradingSchema, FinalAssessmentSchema
from schemas.schedule_interview_request import ScheduleInterviewRequest

load_dotenv()

# ---------------- IMPORTS ----------------
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, APIRouter, Form, WebSocket, WebSocketDisconnect, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Query, Session

import cv2
import numpy as np
import mediapipe as mp
import uuid
import random
import json
import asyncio
import websockets

from database import engine, Base, get_db, SessionLocal
from routes.answer_routes import router as answer_router
from routes.memberdashboard_routes import router as memberdashboard_router
from routes.auth_routes import router as auth_router
from core.session_store import INTERVIEW_SESSIONS

# 🛠️ CLEANED MODELS BLOCK
from models.question import Question, CourseProgram # Pulls your validated enum directly from question.py
from models.model import Candidate, Panel, PanelMember, Interview, User
from models.answer import Answer

from openai import OpenAI
from google import genai
from google.genai import types



from typing import Annotated, Any, Dict, Optional, List
from pydantic import BaseModel
from datetime import datetime
from routes import auth_routes as auth

# ---------------- APP INIT ----------------
app = FastAPI()

Base.metadata.create_all(bind=engine)

# ---------------- GEMINI CLIENT ----------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

# 🔥 FFmpeg path
# os.environ["PATH"] += os.pathsep + r"C:\ffmpeg-8.1-essentials_build\bin"
os.environ["PATH"] += os.pathsep + os.getenv("FFMPEG_PATH", "/usr/bin")
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"


# 🔥 Recording path
# RECORDING_BASE_PATH = "C:/Users/saipa/OneDrive/Desktop/Recordings"
RECORDING_BASE_PATH = os.getenv("RECORDING_BASE_PATH", "/tmp/recordings")
os.makedirs(RECORDING_BASE_PATH, exist_ok=True)

app.mount(
    "/videos",
    StaticFiles(directory=RECORDING_BASE_PATH),
    name="videos"
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

FRONTEND_URL = os.getenv("FRONTEND_URL")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ROUTERS ----------------
app.include_router(answer_router)
app.include_router(memberdashboard_router)
app.include_router(auth_router)

mp_face_detection = mp.solutions.face_detection

# ---------------- OPENAI CLIENT ----------------
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=api_key)

print("✅ API KEY LOADED SUCCESSFULLY")
# ---------------- Assembly Ai CLIENT ----------------

ASSEMBLY_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not ASSEMBLY_API_KEY:
    raise ValueError("❌ ASSEMBLYAI_API_KEY not found in .env")

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

# 

# @app.get("/next-question/{interview_id}")
# def get_next_question(interview_id: int, db: Session = Depends(get_db)):

#     interview_key = str(interview_id)

#     # ---------------- INIT SESSION IF NOT EXISTS ----------------
#     if interview_key not in INTERVIEW_SESSIONS:

#         # 🔥 Fetch in sequential order (by ID)
#         questions = db.query(Question).order_by(Question.id).all()

#         if not questions:
#             raise HTTPException(status_code=404, detail="No questions found")

#         INTERVIEW_SESSIONS[interview_key] = {
#             "questions": [q.id for q in questions],
#             "current_index": 0,
#             "completed": False
#         }

#     session = INTERVIEW_SESSIONS[interview_key]

#     # ---------------- CHECK COMPLETION ----------------
#     if session["current_index"] >= len(session["questions"]):
#         session["completed"] = True
#         return {"message": "Interview completed"}

#     # ---------------- FETCH QUESTION ----------------
#     question_id = session["questions"][session["current_index"]]

#     question = db.query(Question).filter(Question.id == question_id).first()

#     if not question:
#         raise HTTPException(status_code=404, detail="Question not found")

#     # ---------------- INCREMENT INDEX ----------------
#     session["current_index"] += 1

#     return question

@app.get("/next-question/{interview_id}")
def get_next_question(interview_id: str, category: str, db: Session = Depends(get_db)):
    interview_key = str(interview_id)

    # ---------------- INIT SESSION IF NOT EXISTS ----------------
    if interview_key not in INTERVIEW_SESSIONS:
        # 🔥 Filter questions ONLY by the specific session_category
        questions = db.query(Question).filter(Question.category == category).order_by(Question.id).all()

        if not questions:
            raise HTTPException(status_code=404, detail="No questions found for this document session.")

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

    # Increment for next time
    session["current_index"] += 1
 
    return question


# ---------------- SAVE FULL VIDEO ----------------
# @app.post("/save-video/{interview_id}")
# async def save_video(
#     interview_id: int,
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db)
# ):
#     try:
#         # 🔥 Ensure directory exists
#         os.makedirs(RECORDING_BASE_PATH, exist_ok=True)

#         # 🔥 Create filename (IMPORTANT CHANGE)
#         filename = f"{interview_id}.webm"

#         # 🔥 Build full path
#         video_path = os.path.join(RECORDING_BASE_PATH, filename)

#         # 🔥 Normalize (OS safe)
#         video_path = os.path.normpath(video_path)

#         # 🔥 Save file
#         contents = await file.read()
#         with open(video_path, "wb") as f:
#             f.write(contents)

#         # ---------------- FETCH INTERVIEW ----------------
#         interview = db.query(Interview).filter(Interview.id == interview_id).first()

#         if not interview:
#             raise HTTPException(status_code=404, detail="Interview not found")

#         # ---------------- UPDATE INTERVIEW ----------------
#         # ✅ STORE ONLY FILE NAME (NOT FULL PATH)
#         interview.video_path = filename
#         interview.status = "Completed"

#         # ---------------- UPDATE CANDIDATE ----------------
#         candidate = db.query(Candidate).filter(
#             Candidate.id == interview.candidate_id
#         ).first()

#         if candidate:
#             candidate.video_path = filename

#         db.commit()

#         # ✅ Return full accessible URL (optional but useful)
#         video_url = f"http://127.0.0.1:8000/videos/{filename}"

#         return {
#             "message": "Video saved and updated successfully",
#             "video_filename": filename,
#             "video_url": video_url
#         }

#     except Exception as e:
#         print("❌ SAVE VIDEO ERROR:", e)
#         raise HTTPException(status_code=500, detail=str(e))

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
            model="gpt-4o-mini",
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
    interview_category: Optional[str] = None

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

# @app.post("/api/schedule-interview")
# def schedule_interview(data: InterviewRequest, db: Session = Depends(get_db)):
#     try:
#         # Generate the unique identifier tracking key for the session handshake
#         interview_id = generate_interview_id()
        
#         # 🛠️ Validate and convert incoming frontend string to your Python CourseProgram Enum
#         db_course = None
#         if data.student_course_program:
#             try:
#                 db_course = CourseProgram(data.student_course_program)
#             except ValueError:
#                 raise HTTPException(
#                     status_code=400, 
#                     detail=f"Invalid course program validation match. Choose from: {[c.value for c in CourseProgram]}"
#                 )

#         # 1. Create the candidate with the course program assigned directly to its proper model field
#         candidate = Candidate(
#             name=data.student_full_name,
#             email=data.student_email,
#             phone=data.student_mobile,
#             interview_id=interview_id,
#             student_father_mother_name=data.student_father_mother_name,
#             student_dob=data.student_dob,
#             student_gender=data.student_gender,
#             student_category=data.student_category,
#             student_alt_mobile=data.student_alt_mobile,
#             student_current_address=data.student_current_address,
#             student_permanent_address=data.student_permanent_address,
#             student_course_program=data.student_course_program,
            
#             # 🔥 SAVED DIRECTLY IN CANDIDATE TABLE AS ENUM
#             course_program=db_course,
            
#             student_department_branch=data.student_department_branch,
#             student_university=data.student_university,
#             student_enrollment_no=data.student_enrollment_no,
#             student_academic_year=data.student_academic_year,
#             student_cgpa=data.student_cgpa,
#             student_skills=data.student_skills,
#             student_certifications=data.student_certifications,
#             student_projects=data.student_projects,
#             student_experience=data.student_experience,
#             student_strengths=data.student_strengths,
#             student_weaknesses=data.student_weaknesses,
#             student_career_objective=data.student_career_objective,
#             student_declaration=data.student_declaration
#         )
        
#         db.add(candidate)
#         db.commit()
#         db.refresh(candidate)
        
#         # 2. Handle routing / scheduling panel structures
#         if data.panel_id:
#             panel = db.query(Panel).filter(Panel.id == data.panel_id).first()
#             if not panel:
#                 raise HTTPException(status_code=404, detail="Selected evaluation panel not found")
#         else:
#             # Fallback named generation matching the course value
#             fallback_name = f"{db_course.value if db_course else 'General'} Panel"
#             panel = Panel(
#                 panel_name=data.panel_name or fallback_name,
#                 created_by=1  
#             )
#             db.add(panel)
#             db.commit()
#             db.refresh(panel)
            
#             # Add corresponding assigned panel members
#             if data.member_user_ids:
#                 for user_id in data.member_user_ids:
#                     role = "chairman" if user_id == data.chairman_user_id else "member"
#                     panel_member = PanelMember(
#                         panel_id=panel.id,
#                         user_id=user_id,
#                         role=role
#                     )
#                     db.add(panel_member)
#                 db.commit()
        
#         # 3. Complete structural interview event generation setup mapping to your candidate
#         interview = Interview(
#             candidate_id=candidate.id,
#             panel_id=panel.id,
#             scheduled_at=f"{data.interview_date} {data.start_time}",
#             status="Scheduled",
#             created_by=1,
#             interview_category=data.interview_category or (db_course.value if db_course else "General"),   
#             interview_id=interview_id,    
#         )
        
#         db.add(interview)
#         db.commit()
#         db.refresh(interview)
        
#         return {
#             "success": True,
#             "message": "Interview scheduled successfully and course assigned directly to candidate record.",
#             "interview_id": interview_id,
#             "data": {
#                 "candidate_id": candidate.id,
#                 "panel_id": panel.id,
#                 "interview_id": interview_id
#             }
#         }
        
#     except HTTPException as he:
#         db.rollback()
#         raise he
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/interviews/latest")
def get_latest_interview(db: Session = Depends(get_db)):

    latest = db.query(Interview).order_by(Interview.id.desc()).first()

    if not latest:
        return {"success": False, "message": "No interviews found"}

    candidate = latest.candidate
    panel = latest.panel
    members = db.query(PanelMember).filter(
        PanelMember.panel_id == panel.id
    ).all()

    return {
        "success": True,
        "data": {
            "candidate": candidate,
            "interview": latest,
            "panel": panel,
            "members": members
        }
    }


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


# BASE_URL = "http://127.0.0.1:8000"
# ✅ Use env variable
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
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
    # 🔍 Check candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # 📁 Create uploads folder if not exists
    os.makedirs("uploads", exist_ok=True)

    # 🧠 Create proper saved filename
    saved_filename = f"{candidate_id}_{file_type}_{file.filename}"
    file_location = os.path.join("uploads", saved_filename)

    # 💾 Save file
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)

    # 🗂️ Update DB with correct filename
    if file_type == "photo":
        candidate.photo_filename = saved_filename
    elif file_type == "resume":
        candidate.resume_filename = saved_filename
    elif file_type == "idproof":
        candidate.idproof_filename = saved_filename
    elif file_type == "certificates":
        candidate.certificates_filename = saved_filename
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    db.commit()

    # 🔗 Return file URL (important for frontend)
    file_url = f"{BASE_URL}/uploads/{saved_filename}"

    return {
        "success": True,
        "message": "File uploaded successfully",
        "file_url": file_url
    }


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

@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):

    await websocket.accept()
    print("✅ Angular client connected")

    assembly_url = "wss://streaming.assemblyai.com/v3/ws?sample_rate=16000&speech_model=u3-rt-pro"

    try:
        async with websockets.connect(
            assembly_url,
            additional_headers={"Authorization": ASSEMBLY_API_KEY}
        ) as assembly_ws:

            print("✅ Connected to AssemblyAI")

            buffer = b""  # 🔥 accumulate audio chunks

            # 🔥 SEND AUDIO (Angular → AssemblyAI)
            async def send_audio():
                try:
                    while True:
                        chunk = await websocket.receive_bytes()

                        if not chunk:
                            continue

                        print("📤 Sending RAW PCM:", len(chunk))
                        await assembly_ws.send(chunk)

                except WebSocketDisconnect:
                    print("❌ Angular disconnected")
            # 🔥 RECEIVE TRANSCRIPT (AssemblyAI → Angular)
            async def receive_transcript():
                try:
                    async for message in assembly_ws:
                        try:
                            data = json.loads(message)
                        except Exception:
                            print("⚠️ Invalid JSON:", message)
                            continue

                        print("📩 AssemblyAI:", data)

                        if data.get("type") == "Turn":
                            if data.get("end_of_turn"):  # ✅ ONLY FINAL TEXT
                                await websocket.send_text(json.dumps(data))

                except Exception as e:
                    print("❌ AssemblyAI error:", e)

            # 🔥 run both
            await asyncio.gather(send_audio(), receive_transcript())

    except Exception as e:
        print("❌ WebSocket Error:", e)


@app.post("/api/candidate/login")
def candidate_login(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    phone = payload.get("phone")

    # 🔒 Basic validation
    if not email or not phone:
        return {
            "success": False,
            "message": "Email and phone are required"
        }

    # 🔍 Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.email == email).first()

    # =========================
    # ✅ EXISTING USER LOGIN
    # =========================
    if candidate:
        if candidate.phone != phone:
            return {
                "success": False,
                "message": "Invalid phone number"
            }

        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
            }
        }

    # =========================
    # 🔥 NEW USER → AUTO CREATE
    # =========================
    import uuid

    new_candidate = Candidate(
        name=email.split("@")[0],
        email=email,
        phone=phone,
        interview_id=str(uuid.uuid4())
    )

    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    return {
        "success": True,
        "message": "User created & login successful",
        "data": {
            "id": new_candidate.id,
            "name": new_candidate.name,
            "email": new_candidate.email,
            "interview_id": new_candidate.interview_id
        }
    }

# Use the correct production model strings
PRIMARY_MODEL = "gemini-2.5-flash"
# PRIMARY_MODEL = "gemini-3-flash-preview"  # ✅ Updated to latest flash model for best performance

# ================= ENFORCED JSON SCHEMAS =================
class QuestionItem(BaseModel):
    question_text: str
    expected_answer: str
    difficulty: str = "Medium"

class QuestionGenerationSchema(BaseModel):
    detected_subject: str
    questions: List[QuestionItem]

class GradingSchema(BaseModel):
    score: int
    feedback: str

@app.post("/api/grade-answer/{answer_id}")
async def grade_answer_with_pdf(
    answer_id: int, 
    pdf_file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        # 1. Fetch the answer and question from DB
        answer_record = db.query(Answer).filter(Answer.id == answer_id).first()
        if not answer_record:
            raise HTTPException(status_code=404, detail="Answer record not found")
        
        question_record = db.query(Question).filter(Question.id == answer_record.question_id).first()

        # 2. Read PDF bytes
        pdf_content = await pdf_file.read()

        # 3. Construct the prompt
        prompt = f"""
        You are an expert interviewer. Grade the candidate's answer based ONLY on the provided PDF document.
        
        QUESTION: {question_record.question_text}
        EXPECTED KEY POINTS: {question_record.expected_answer}
        CANDIDATE'S ACTUAL ANSWER: {answer_record.answer_text}
        
        TASK:
        - Compare the candidate's answer with the technical facts in the PDF.
        - Assign a score from 0 to 10.
        - Provide a short, professional feedback sentence.
        
        Return ONLY a JSON object:
        {{
            "score": integer,
            "feedback": "string"
        }}
        """

        # 4. Call Gemini 2.0 Flash
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=pdf_content, mime_type="application/pdf"),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # 5. Parse Gemini response
        grading_result = json.loads(response.text)

        # 6. Update Database
        answer_record.ai_score = grading_result.get("score")
        answer_record.ai_response = grading_result.get("feedback")
        
        db.commit()
        db.refresh(answer_record)

        return {
            "success": True,
            "score": answer_record.ai_score,
            "feedback": answer_record.ai_response
        }

    except Exception as e:
        db.rollback()
        print(f"❌ Grading Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def grade_with_expected_answer(answer_id: int, question_id: int, candidate_answer: str):
    db = SessionLocal()
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            print(f"❓ Question ID {question_id} missing from lookup bank.")
            return

        expected = question.expected_answer or "No baseline verification reference value established."

        prompt = f"""
        You are a seasoned technical interviewer grading a candidate's answer response string.
        
        QUESTION CONTEXT: {question.question_text}
        EXPECTED KEY ANSWER VALUES: {expected}
        CANDIDATE ACTUAL RESPONSE STRING: {candidate_answer}

        Task Core Guidelines:
        - Deeply evaluate semantic concept alignment logic over exact textual sequence matches.
        - Output an integer score grading evaluation on a strict 0 to 10 scale.
        - Populate a clean feedback summary statement mapping observations fairly.
        """

        response = genai_client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GradingSchema
            )
        )

        result = json.loads(response.text)
        final_score = int(result.get("score", 0))
        final_feedback = result.get("feedback", "Grading evaluation cycle finalized.")

        db.query(Answer).filter(Answer.id == answer_id).update({
            "ai_score": final_score,
            "ai_response": final_feedback
        })
        db.commit()
        print(f"✅ AI Grading Complete for Answer Record ID: {answer_id} | Assigned Evaluation Score: {final_score}")

    except Exception as e:
        db.rollback()
        print(f"❌ Critical Core AI Background Thread Failure: {str(e)}")
        db.query(Answer).filter(Answer.id == answer_id).update({
            "ai_response": f"AI Evaluation Pipeline Drop: {str(e)[:45]}..."
        })
        db.commit()
    finally:
        db.close()


# --- THE UPDATED ROUTE ---
@app.post("/api/submit-and-grade")
async def submit_and_grade(
    background_tasks: BackgroundTasks,
    candidate_id: int = Form(...),
    question_id: int = Form(...),
    answer_text: str = Form(...),
    panel_id: int = Form(...),
    db: Session = Depends(get_db)
):
    new_ans = Answer(
        candidate_id=candidate_id, 
        question_id=question_id, 
        answer_text=answer_text, 
        panel_id=panel_id,
        ai_response="Processing..."
    )
    db.add(new_ans)
    db.commit()
    db.refresh(new_ans)

    # Trigger background evaluation task loop
    background_tasks.add_task(grade_with_expected_answer, new_ans.id, question_id, answer_text)

    return {"success": True, "message": "Answer received!", "answer_id": new_ans.id}


@app.post("/api/upload-and-generate-questions")
async def upload_pdf_and_generate(
    file: UploadFile = File(...), 
    num_questions: int = Form(3),        # 👈 Changed to Form so it cleanly extracts from Angular FormData
    course: CourseProgram = Form(...),   # 👈 Automatically validates against your 6 options!
    db: Session = Depends(get_db) 
):
    try:
        # Read the file stream incoming from the upload pipeline
        pdf_bytes = await file.read()
        
        prompt = f"""
        Analyze this PDF document cleanly.
        1. Identify the high-level professional subject domain matching a {course.value} program curriculum.
        2. Generate exactly {num_questions} structured interview questions anchored directly to the source text data.
        3. For each item, provide a comprehensive 'expected_answer' context block.
        4. Infer a structural difficulty tier ('Easy', 'Medium', or 'Hard') based on the complexity of the section topic parsed.
        """

        # Call Gemini using the structured JSON schema rules setup
        response = genai_client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuestionGenerationSchema  # Enforces structural text output consistency
            )
        )

        # Parse output payload from model pipeline strings
        data = json.loads(response.text)
        subject = data.get("detected_subject", "General AI Concept").upper()
        session_category = f"{subject}_{uuid.uuid4().hex[:4]}"

        # Iterate over structural dictionary lists 
        for q in data.get('questions', []):
            new_question = Question(
                question_text=q['question_text'].strip(),
                expected_answer=q['expected_answer'].strip(),
                category=session_category,
                course=course,                   # 👈 Saves natively as your clean enum key
                difficulty=q.get('difficulty', 'Medium').strip(), # Captures AI inferred complexity level
                time_limit=120                   # Standard default limit (seconds) for AI questions
            )
            db.add(new_question)
        
        # Commit transactional operations block safely to your database 
        db.commit()

        return {
            "success": True, 
            "category": session_category, 
            "course": course.value,              # 👈 Returns clean string ("B-Tech", "MCA", etc.)
            "display_subject": subject,
            "count": len(data.get('questions', []))
        }

    except Exception as e:
        db.rollback()                            # Flushes changes out of scope bounds upon drop anomalies
        print(f"❌ ERROR inside generation sequence: {str(e)}")
        return {"success": False, "error": str(e)}   

# @app.get("/api/get-questions-by-candidate/{candidate_id}")
# def get_questions_by_candidate(candidate_id: int, db: Session = Depends(get_db)):
#     # 1. Fetch candidate context profile matching the incoming primary key ID
#     candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
#     if not candidate:
#         raise HTTPException(status_code=404, detail="Candidate profile data not found")
    
#     # 2. Extract course variable (Check the SQLEnum column first, fallback to standard String field)
#     raw_course = candidate.course_program or candidate.student_course_program
#     if not raw_course:
#         raise HTTPException(status_code=400, detail="No course program assignment mapping found on this student profile")
    
#     # Extract string value if it's a structural Enum instance
#     course_str = raw_course.value if hasattr(raw_course, 'value') else str(raw_course)
    
#     # 3. Pull all matching sequential questions out of the question_bank table
#     questions = db.query(Question).filter(Question.course == course_str).all()
    
#     # Optional Fallback Rule: If no items exist under the explicit tag, pull "General" items
#     if not questions:
#         questions = db.query(Question).filter(Question.category.ilike("%General%")).all()
        
#     return {
#         "success": True,
#         "candidate_id": candidate.id,
#         "candidate_name": candidate.name,
#         "matched_course": course_str,
#         "total_questions": len(questions),
#         "questions": [
#             {
#                 "id": q.id,
#                 "question_text": q.question_text,
#                 "expected_answer": q.expected_answer,
#                 "category": q.category,
#                 "difficulty": q.difficulty,
#                 "time_limit": q.time_limit if q.time_limit else 50
#             }
#             for q in questions
#         ]
#     }

class StudentItem(BaseModel):
    name: str
    email: str
    phone: str
    department_branch: str

class BulkRegistrationPayload(BaseModel):
    course_program: str
    students: List[StudentItem]

@app.post("/api/save-bulk-students")
def save_bulk_students(payload: BulkRegistrationPayload, db: Session = Depends(get_db)):
    try:
        inserted_count = 0
        
        # Loop through the parsed array rows extracted by your Angular app
        for student in payload.students:
            # Prepare an individual table record object mapping properties
            db_candidate = Candidate(
                name=student.name,
                email=student.email,
                phone=student.phone,
                course_program=payload.course_program,       # Applied globally from your select dropdown
                department_branch=student.department_branch  # Extracted row-by-row from Excel
            )
            db.add(db_candidate)
            inserted_count += 1
            
        # Commit the transaction to save all records cleanly
        db.commit()
        
        print(f"🎉 Successfully persisted {inserted_count} student records inside 'candidates' table.")
        return {"success": True, "inserted_count": inserted_count}

    except Exception as e:
        db.rollback()  # Rollback if an unexpected breakdown happens to prevent corrupted tables
        print(f"❌ Critical Database Write Anomaly: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database operational write failure: {str(e)}")
    
# 💡 FIX: Make sure it's attached directly to @app if written inside main.py
@app.get("/api/candidate-courses/{email}")
async def get_candidate_courses(email: str, db: Session = Depends(get_db)): 
    """
    Looks up registration entries using the student's unique email.
    Gathers all registered courses even if they have different sequential IDs.
    """
    # 1. Query all entries matching this email address
    registration_records = db.query(Candidate).filter(Candidate.email == email).all()
    
    if not registration_records:
        raise HTTPException(
            status_code=404, 
            detail=f"No registration history found for email address: {email}"
        )
    
    # 2. Map out a unique list of their courses (e.g., ["B-Tech", "MCA"])
    unique_allowed_tracks = list(set([record.course_program for record in registration_records]))
    
    return {
        "success": True,
        "candidate_name": registration_records[0].name,
        "allowed_courses": unique_allowed_tracks
    }


@app.get("/api/get-questions-by-candidate/{candidate_id}")
async def get_self_assessment_questions(
    candidate_id: int,
    selected_course: str,
    db: Session = Depends(get_db)
):
    """
    1. Grabs the email associated with candidate_id.
    2. Verifies that the email profile is registered for the selected_course on ANY row.
    3. Fetches 5 random assessment questions from the question bank.
    """
    
    # -----------------------------------------------------------------
    # STEP 1: RESOLVE ID TO EMAIL & VALIDATE CROSS-ROW PERMISSION
    # -----------------------------------------------------------------
    # Find the primary student profile row first to grab their email address
    current_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not current_candidate:
        raise HTTPException(status_code=404, detail="Candidate profile row not found.")

    # Cross-verify using the email to check if they own a row matching the selected_course
    registration_check = (
        db.query(Candidate)
        .filter(Candidate.email == current_candidate.email, Candidate.course_program == selected_course)
        .first()
    )
    
    if not registration_check:
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied. Candidate is not registered for the '{selected_course}' track."
        )

    # -----------------------------------------------------------------
    # STEP 2: CONVERT STRING ENTRY TO DB ENUM TYPE
    # -----------------------------------------------------------------
    try:
        course_mapping = {
            "BBA": CourseProgram.BBA,
            "MBA": CourseProgram.MBA,
            "B-Tech": CourseProgram.B_TECH,
            "MCA": CourseProgram.MCA,
            "B.Com": CourseProgram.B_COM,
            "M.Com": CourseProgram.M_COM
        }

        target_enum_course = course_mapping.get(selected_course)

        if not target_enum_course:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid course: {selected_course}"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Selected course track value '{selected_course}' is out of alignment."
        )

    # -----------------------------------------------------------------
    # STEP 3: FETCH RANDOM QUESTIONS FROM THE BANK
    # -----------------------------------------------------------------
    all_questions = db.query(Question).all()

    for q in all_questions:
        print(
            f"ID={q.id} | COURSE={q.course}"
        )

    questions = (
        db.query(Question)
        .filter(Question.course == target_enum_course)
        .order_by(func.random())
        .limit(5)
        .all()
    )

    print("Questions Found:", len(questions))
    print("Selected Course:", selected_course)
    print("Enum Course:", target_enum_course)

    if not questions:
        raise HTTPException(
            status_code=444, 
            detail=f"The question bank currently does not have active evaluation inventory seeded for the track: {selected_course}"
        )

    # -----------------------------------------------------------------
    # STEP 4: RETURN STRUCTURAL FRONTEND PAYLOAD
    # -----------------------------------------------------------------
    return {
        "success": True,
        # Make sure we use registration_check's explicit data here to align IDs perfectly!
        "candidate_id": registration_check.id, 
        "candidate_name": registration_check.name,
        "matched_course": target_enum_course.value,
        "total_questions": len(questions),
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "time_limit": q.time_limit,
                "difficulty": q.difficulty,
                "category": q.category
            } for q in questions
        ]
    }

@app.post("/api/self-assessment/submit-answer")
async def submit_self_assessment_answer(
    background_tasks: BackgroundTasks,
    candidate_id: int = Form(...),
    assessment_id: str = Form(...),
    question_id: int = Form(...),
    answer_text: str = Form(...),
    course: str = Form(...),
    db: Session = Depends(get_db)
):

    new_answer = SelfAssessmentAnswer(
        candidate_id=candidate_id,
        assessment_id=assessment_id,
        question_id=question_id,
        answer_text=answer_text,
        course=course,
        ai_response="Processing...",
        status="Processing"
    )

    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)

    # Trigger AI grading in background
    background_tasks.add_task(
        grade_self_assessment_answer,
        new_answer.id,
        question_id,
        answer_text
    )

    return {
        "success": True,
        "message": "Answer received successfully.",
        "answer_id": new_answer.id,
        "assessment_id": assessment_id
    }


async def grade_self_assessment_answer(
    answer_id: int,
    question_id: int,
    candidate_answer: str
):

    db = SessionLocal()

    try:

        question = db.query(Question)\
            .filter(Question.id == question_id)\
            .first()

        if not question:
            print(
                f"❓ Question ID {question_id} not found."
            )
            return

        expected = (
            question.expected_answer
            or "No reference answer available."
        )

        prompt = f"""
        You are a seasoned technical interviewer grading a candidate's answer.

        QUESTION:
        {question.question_text}

        EXPECTED ANSWER:
        {expected}

        CANDIDATE ANSWER:
        {candidate_answer}

        Instructions:
        - Evaluate concept understanding.
        - Do not require exact wording.
        - Give a score from 0 to 10.
        - Give detailed feedback.

        Return JSON:
        {{
          "score": 8,
          "feedback": "Good answer..."
        }}
        """

        response = genai_client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GradingSchema
            )
        )

        result = json.loads(response.text)

        final_score = int(
            result.get("score", 0)
        )

        final_feedback = result.get(
            "feedback",
            "Evaluation completed."
        )

        db.query(SelfAssessmentAnswer)\
            .filter(
                SelfAssessmentAnswer.id == answer_id
            )\
            .update({

                "ai_score": final_score,

                "ai_response": final_feedback,

                "status": "Completed"

            })

        db.commit()

        print(
            f"✅ Self Assessment Graded | "
            f"Answer ID: {answer_id} | "
            f"Score: {final_score}"
        )

    except Exception as e:

        db.rollback()

        error_message = str(e)

        print(
            f"❌ Self Assessment Grading Error: {error_message}"
        )

        if (
            "RESOURCE_EXHAUSTED" in error_message
            or "429" in error_message
            or "503" in error_message
        ):

            db.query(SelfAssessmentAnswer)\
                .filter(
                    SelfAssessmentAnswer.id == answer_id
                )\
                .update({

                    "ai_score": 0,

                    "ai_response":
                        "AI evaluation temporarily unavailable due to quota limits.",

                    "status": "Pending"

                })

        else:

            db.query(SelfAssessmentAnswer)\
                .filter(
                    SelfAssessmentAnswer.id == answer_id
                )\
                .update({

                    "ai_response":
                        f"AI Evaluation Error: {error_message[:100]}",

                    "status": "Failed"

                })

        db.commit()

    finally:
        db.close()


@app.post("/api/self-assessment/generate-final-result/{assessment_id}")
async def generate_final_self_assessment_result(
    assessment_id: str,
    db: Session = Depends(get_db)
):

    answers = db.query(SelfAssessmentAnswer)\
        .filter(
            SelfAssessmentAnswer.assessment_id == assessment_id
        )\
        .all()

    if not answers:
        raise HTTPException(
            status_code=404,
            detail="No answers found for this assessment."
        )

    candidate_id = answers[0].candidate_id

    total_marks = sum(
        (a.ai_score or 0)
        for a in answers
    )

    total_questions = len(answers)

    feedback_text = "\n".join([
        a.ai_response or ""
        for a in answers
    ])

    course = answers[0].course

    try:

        prompt = f"""
        You are an expert technical interviewer.

        Assessment Statistics:

        Total Questions: {total_questions}

        Total Marks: {total_marks}

        Individual Feedback:

        {feedback_text}

        Return ONLY JSON.

        Required JSON Structure:

        {{
            "strengths": [
                "strength 1",
                "strength 2"
            ],
            "improvements": [
                "improvement 1",
                "improvement 2"
            ],
            "summary": "overall assessment summary"
        }}
        """

        response = genai_client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FinalAssessmentSchema
            )
        )

        final_response = response.text

    except Exception as e:

        print(
            f"⚠️ Failed generating overall feedback: {str(e)}"
        )

        final_response = (
            "Assessment completed successfully. "
            "Overall AI summary unavailable."
        )

    existing = db.query(SelfAssessmentResult)\
        .filter(
            SelfAssessmentResult.assessment_id == assessment_id
        )\
        .first()

    if existing:

        existing.final_marks = total_marks
        existing.final_response = final_response

        db.commit()

        return {
            "success": True,
            "message": "Result updated.",
            "result_id": existing.id
        }

    result = SelfAssessmentResult(
        candidate_id=candidate_id,
        assessment_id=assessment_id,
        course=course,
        final_marks=total_marks,
        final_response=final_response
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "success": True,
        "message": "Final result generated.",
        "result_id": result.id,
        "final_marks": total_marks
    }

# @app.post("/api/self-assessment/generate-final-result/{assessment_id}")
# async def generate_final_self_assessment_result(
#     assessment_id: str,
#     db: Session = Depends(get_db)
# ):

#     answers = db.query(SelfAssessmentAnswer)\
#         .filter(
#             SelfAssessmentAnswer.assessment_id == assessment_id
#         )\
#         .all()

#     if not answers:
#         raise HTTPException(
#             status_code=404,
#             detail="No answers found for this assessment."
#         )

#     candidate_id = answers[0].candidate_id

#     total_marks = sum(
#         (a.ai_score or 0)
#         for a in answers
#     )

#     total_questions = len(answers)

#     average_score = (
#         total_marks / total_questions
#         if total_questions > 0
#         else 0
#     )

#     course = "Unknown"

#     strengths = []
#     improvements = []

#     if average_score >= 8:

#         strengths = [
#             "Strong understanding of core concepts",
#             "Consistent performance across questions",
#             "Demonstrated good technical knowledge"
#         ]

#     elif average_score >= 5:

#         strengths = [
#             "Basic conceptual understanding",
#             "Able to answer most questions"
#         ]

#         improvements = [
#             "Needs deeper technical knowledge",
#             "Should improve explanation quality"
#         ]

#     else:

#         improvements = [
#             "Requires additional preparation",
#             "Needs improvement in fundamentals",
#             "Should practice more technical concepts"
#         ]

#     final_response = json.dumps({
#         "strengths": strengths,
#         "improvements": improvements,
#         "summary":
#             f"Candidate scored {total_marks} marks across "
#             f"{total_questions} questions with an average score "
#             f"of {round(average_score, 2)}."
#     })

#     existing = db.query(SelfAssessmentResult)\
#         .filter(
#             SelfAssessmentResult.assessment_id == assessment_id
#         )\
#         .first()

#     if existing:

#         existing.final_marks = total_marks
#         existing.final_response = final_response

#         db.commit()

#         return {
#             "success": True,
#             "message": "Result updated.",
#             "result_id": existing.id,
#             "final_marks": total_marks
#         }

#     result = SelfAssessmentResult(
#         candidate_id=candidate_id,
#         assessment_id=assessment_id,
#         course=course,
#         final_marks=total_marks,
#         final_response=final_response
#     )

#     db.add(result)
#     db.commit()
#     db.refresh(result)

#     return {
#         "success": True,
#         "message": "Final result generated.",
#         "result_id": result.id,
#         "final_marks": total_marks
#     }

@app.get("/api/self-assessment/result/{assessment_id}")
async def get_self_assessment_result(
    assessment_id: str,
    db: Session = Depends(get_db)
):

    result = db.query(SelfAssessmentResult)\
        .filter(
            SelfAssessmentResult.assessment_id == assessment_id
        )\
        .first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Assessment result not found."
        )

    return {
        "success": True,
        "result": {
            "candidate_id": result.candidate_id,
            "assessment_id": result.assessment_id,
            "course": result.course,
            "final_marks": result.final_marks,
            "final_response": result.final_response,
            "completed_at": result.completed_at
        }
    }

@app.get("/api/interviews/check-schedule/{email}")
async def check_interview_schedule(
    email: str,
    db: Session = Depends(get_db)
):

    # Find all candidate records for this email
    candidate_ids = [
        c.id
        for c in db.query(Candidate)
        .filter(Candidate.email == email)
        .all()
    ]

    if not candidate_ids:
        return {
            "success": True,
            "status": "none",
            "message": "Candidate not found."
        }

    # Find latest interview among all candidate records
    interview = (
        db.query(Interview)
        .filter(
            Interview.candidate_id.in_(candidate_ids)
        )
        .order_by(Interview.id.desc())
        .first()
    )

    if not interview:
        return {
            "success": True,
            "status": "none",
            "message": "No interview assigned."
        }

    # ----------------------------------
    # COMPLETED
    # ----------------------------------

    if interview.status == "Completed":
        return {
            "success": True,
            "status": "completed",
            "message": "Interview already completed.",
            "interview": {
                "candidate_id": interview.candidate_id,
                "interview_id": interview.interview_id,
                "panel_id": interview.panel_id,
                "course": interview.interview_category,
                "scheduled_at": interview.scheduled_at
            }
        }

    # ----------------------------------
    # CANCELLED
    # ----------------------------------

    if interview.status == "Cancelled":
        return {
            "success": True,
            "status": "cancelled",
            "message": "Interview was cancelled.",
            "interview": {
                "candidate_id": interview.candidate_id,
                "interview_id": interview.interview_id,
                "panel_id": interview.panel_id,
                "course": interview.interview_category,
                "scheduled_at": interview.scheduled_at
            }
        }

    # ----------------------------------
    # DATE PARSE
    # ----------------------------------

    try:

        scheduled_dt = datetime.strptime(
            interview.scheduled_at,
            "%Y-%m-%d %H:%M"
        )

    except Exception:

        print(
            "Scheduled Date Parse Error:",
            interview.scheduled_at
        )

        raise HTTPException(
            status_code=500,
            detail="Invalid scheduled_at format."
        )

    now = datetime.now()

    # ----------------------------------
    # NOT TODAY
    # ----------------------------------

    if scheduled_dt.date() != now.date():

        return {
            "success": True,
            "status": "none",
            "message": "No interview scheduled today."
        }

    diff_minutes = (
        scheduled_dt - now
    ).total_seconds() / 60

    # ----------------------------------
    # UPCOMING
    # ----------------------------------

    if diff_minutes > 15:

        return {
            "success": True,
            "status": "upcoming",
            "message": "Interview scheduled later today.",
            "interview": {
                "candidate_id": interview.candidate_id,
                "interview_id": interview.interview_id,
                "panel_id": interview.panel_id,
                "course": interview.interview_category,
                "scheduled_at": interview.scheduled_at
            }
        }

    # ----------------------------------
    # READY
    # ----------------------------------

    if 0 <= diff_minutes <= 15:

        return {
            "success": True,
            "status": "ready",
            "message": "Interview ready to join.",
            "interview": {
                "candidate_id": interview.candidate_id,
                "interview_id": interview.interview_id,
                "panel_id": interview.panel_id,
                "course": interview.interview_category,
                "scheduled_at": interview.scheduled_at
            }
        }

    # ----------------------------------
    # EXPIRED
    # ----------------------------------

    return {
        "success": True,
        "status": "expired",
        "message": "Interview time has passed.",
        "interview": {
            "candidate_id": interview.candidate_id,
            "interview_id": interview.interview_id,
            "panel_id": interview.panel_id,
            "course": interview.interview_category,
            "scheduled_at": interview.scheduled_at
        }
    }

@app.get("/api/interviews/load-questions/{candidate_id}/{course}")
async def load_scheduled_interview_questions(
    candidate_id: int,
    course: str,
    db: Session = Depends(get_db)
):

    # Verify interview exists for this candidate/course
    interview = (
        db.query(Interview)
        .filter(
            Interview.candidate_id == candidate_id,
            Interview.interview_category == course
        )
        .order_by(Interview.id.desc())
        .first()
    )

    if not interview:
        raise HTTPException(
            status_code=404,
            detail="No scheduled interview found."
        )

    questions = (
        db.query(Question)
        .filter(
            Question.course == course
        )
        .order_by(Question.id.asc())
        .all()
    )

    if not questions:
        raise HTTPException(
            status_code=404,
            detail=f"No questions found for course {course}"
        )

    return {
        "success": True,
        "candidate_id": candidate_id,
        "interview_id": interview.interview_id,
        "course": course,
        "total_questions": len(questions),
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "difficulty": q.difficulty,
                "time_limit": q.time_limit
            }
            for q in questions
        ]
    }

@app.post("/api/interviews/save-video/{interview_code}")
async def save_video(
    interview_code: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:

        # --------------------------------------------------
        # Find Interview using Interview Code
        # --------------------------------------------------

        interview = (
            db.query(Interview)
            .filter(
                Interview.interview_id == interview_code
            )
            .first()
        )

        if not interview:
            raise HTTPException(
                status_code=404,
                detail="Interview not found."
            )

        # --------------------------------------------------
        # Create Recording Folder (if not exists)
        # --------------------------------------------------

        os.makedirs(RECORDING_BASE_PATH, exist_ok=True)

        # --------------------------------------------------
        # File Name
        # Example:
        # IVW-2026-6686.webm
        # --------------------------------------------------

        filename = f"{interview_code}.webm"

        full_path = os.path.join(
            RECORDING_BASE_PATH,
            filename
        )

        full_path = os.path.normpath(full_path)

        # --------------------------------------------------
        # Save Video
        # --------------------------------------------------

        contents = await file.read()

        with open(full_path, "wb") as f:
            f.write(contents)

        # --------------------------------------------------
        # Update Interview
        # --------------------------------------------------

        interview.video_path = filename
        interview.status = "Completed"

        # --------------------------------------------------
        # Update Candidate
        # --------------------------------------------------

        candidate = (
            db.query(Candidate)
            .filter(
                Candidate.id == interview.candidate_id
            )
            .first()
        )

        if candidate:
            candidate.video_path = filename

        db.commit()

        # --------------------------------------------------
        # Response
        # --------------------------------------------------

        # video_url = f"http://127.0.0.1:8000/videos/{filename}" monika
        video_url = f"{BASE_URL}/videos/{filename}"

        return {
            "success": True,
            "message": "Interview completed successfully.",
            "interview_id": interview.interview_id,
            "candidate_id": interview.candidate_id,
            "status": interview.status,
            "video_filename": filename,
            "video_path": filename,
            "video_url": video_url
        }

    except Exception as e:

        db.rollback()

        print("❌ SAVE VIDEO ERROR:", str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save interview recording: {str(e)}"
        )
    
@app.get("/api/candidates/courses")
async def get_available_courses(db: Session = Depends(get_db)):
    courses = (
        db.query(Candidate.course_program)
        .distinct()
        .order_by(Candidate.course_program.asc())
        .all()
    )

    return {
        "success": True,
        "courses": [c[0] for c in courses if c[0]]
    }

@app.get("/api/candidates/course/{course}")
async def get_candidates_by_course(
    course: str,
    db: Session = Depends(get_db)
):

    candidates = (
        db.query(Candidate)
        .filter(
            Candidate.course_program == course
        )
        .order_by(Candidate.name.asc())
        .all()
    )

    return {
        "success": True,
        "course": course,
        "total_candidates": len(candidates),
        "candidates": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "course_program": c.course_program,
                "department_branch": c.department_branch,
                "video_path": c.video_path
            }
            for c in candidates
        ]
    }

@app.post("/api/interviews/schedule")
async def schedule_interview(
    request: ScheduleInterviewRequest,
    db: Session = Depends(get_db)
):
    try:

        candidate = (
            db.query(Candidate)
            .filter(
                Candidate.id == request.candidate_id
            )
            .first()
        )

        if not candidate:
            raise HTTPException(
                status_code=404,
                detail="Candidate not found."
            )

        panel_id = request.panel_id

        # Create panel if required

        if panel_id is None:

            panel = Panel(
                panel_name=request.panel_name,
                created_by=1
            )

            db.add(panel)
            db.commit()
            db.refresh(panel)

            for member_id in request.member_user_ids:

                role = (
                    "chairman"
                    if member_id == request.chairman_user_id
                    else "member"
                )

                db.add(
                    PanelMember(
                        panel_id=panel.id,
                        user_id=member_id,
                        role=role
                    )
                )

            db.commit()

            panel_id = panel.id

        scheduled_at = (
            f"{request.interview_date} "
            f"{request.start_time}"
        )

        interview = Interview(
            candidate_id=request.candidate_id,
            panel_id=panel_id,
            scheduled_at=scheduled_at,
            status="Scheduled",
            created_by=1,
            interview_category=request.interview_category,
            interview_id=request.interview_id
        )

        db.add(interview)
        db.commit()
        db.refresh(interview)

        return {
            "success": True,
            "message": "Interview scheduled successfully.",
            "interview_id": interview.interview_id,
            "interview_db_id": interview.id,
            "panel_id": panel_id
        }

    except Exception as ex:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )