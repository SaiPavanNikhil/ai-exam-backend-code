from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.answer import Answer
from schemas.answer_schema import AnswerCreate

router = APIRouter()

@router.post("/answers")
def save_answer(answer: AnswerCreate, db: Session = Depends(get_db)):

    # ---------------- SAVE ANSWER ----------------
    new_answer = Answer(
        candidate_id=answer.candidate_id,
        interview_id=answer.interview_id,
        question_id=answer.question_id,
        answer_text=answer.answer_text,
        time_taken=answer.time_taken,
        start_time=answer.start_time,
        end_time=answer.end_time,
        panel_id=answer.panel_id,  # 🔥 NEW

    )

    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)

    return {
        "message": "Answer saved successfully"
    }