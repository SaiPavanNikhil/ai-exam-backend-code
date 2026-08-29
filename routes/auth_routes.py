from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.model import User
from database import Base
from sqlalchemy import text
from schemas.answer_schema import AnswerCreate
from models.answer import Answer

router = APIRouter()

# ✅ Register User
@router.post("/register")
def register(data: dict, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.get("email")).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=data.get("name"),
        email=data.get("email"),
        password=data.get("password"),
        role=data.get("role"),
        designation=data.get("designation") ,  # ✅ added
        member_type=data.get("memberType")   # ✅ added
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


# ✅ Login User
@router.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.get("email")).first()

    if not user or user.password != data.get("password"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }


@router.get("/user/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):

    query = text("""
        SELECT name, role, designation
        FROM users
        WHERE id = :user_id
    """)

    result = db.execute(query, {"user_id": user_id}).fetchone()

    if not result:
        return {"message": "User not found"}

    return {
        "name": result.name,
        "role": result.role,
        "designation": result.designation
    }


@router.post("/answers")
def create_answer(answer: AnswerCreate, db: Session = Depends(get_db)):

    new_answer = Answer(
        candidate_id=answer.candidate_id,
        interview_id=answer.interview_id,
        question_id=answer.question_id,
        answer_text=answer.answer_text,
        time_taken=answer.time_taken,
        start_time=answer.start_time,
        end_time=answer.end_time,
        panel_id=answer.panel_id
    )

    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)

    return {
        "message": "Answer saved successfully",
        "answer_id": new_answer.id
    }