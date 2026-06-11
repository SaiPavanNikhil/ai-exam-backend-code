from pydantic import BaseModel

class SaveAnswerRequest(BaseModel):
    candidate_id: int
    interview_id: str
    question_id: int
    answer_text: str
    time_taken: int