from pydantic import BaseModel

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    category: str | None
    difficulty: str | None
    time_limit: int

    class Config:
        orm_mode = True