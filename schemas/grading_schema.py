from pydantic import BaseModel
from typing import List


class GradingSchema(BaseModel):
    score: int
    feedback: str


class FinalAssessmentSchema(BaseModel):
    strengths: List[str]
    improvements: List[str]
    summary: str