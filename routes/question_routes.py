from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.question import Question

router = APIRouter(prefix="/questions", tags=["Questions"])

# ---------------- GET ALL QUESTIONS ----------------
@router.get("/")
def get_questions(db: Session = Depends(get_db)):
    return db.query(Question).all()


# ---------------- GET QUESTION BY ID ----------------
@router.get("/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)):

    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return question


# ---------------- CREATE QUESTION ----------------
@router.post("/")
def create_question(question_data: dict, db: Session = Depends(get_db)):

    new_question = Question(
        question_text=question_data.get("question_text"),
        expected_answer=question_data.get("expected_answer"),
        difficulty=question_data.get("difficulty"),
        category=question_data.get("category")
    )

    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return {"message": "Question created", "id": new_question.id}


# ---------------- UPDATE QUESTION ----------------
@router.put("/{question_id}")
def update_question(question_id: int, data: dict, db: Session = Depends(get_db)):

    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.question_text = data.get("question_text", question.question_text)
    question.expected_answer = data.get("expected_answer", question.expected_answer)
    question.difficulty = data.get("difficulty", question.difficulty)
    question.category = data.get("category", question.category)

    db.commit()

    return {"message": "Question updated"}


# ---------------- DELETE QUESTION ----------------
@router.delete("/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):

    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    db.delete(question)
    db.commit()

    return {"message": "Question deleted"}