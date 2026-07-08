from pydantic import BaseModel
from typing import Dict, Any


class VideoAnalysisRequest(BaseModel):
    interview_id: str
    candidate_id: int
    interview_mode: str
    analysis: Dict[str, Any]