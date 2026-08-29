from pydantic import BaseModel

class AnswerCreate(BaseModel):
    candidate_id: int
    interview_id: int   # 🔥 REQUIRED
    question_id: int
    answer_text: str
    time_taken: int

    start_time: int     # 🔥 REQUIRED
    end_time: int       # 🔥 REQUIRED

    panel_id: int   # 🔥 NEW