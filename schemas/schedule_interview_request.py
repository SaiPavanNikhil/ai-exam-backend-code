from typing import List, Optional

from pydantic import BaseModel

class ScheduleInterviewRequest(BaseModel):
    interview_id: str

    course_id: int
    subject_id: Optional[int] = None

    candidate_ids: List[int]

    interview_date: str
    start_time: str
    end_time: str

    interview_name: str

    panel_id: Optional[int] = None

    panel_name: Optional[str] = None
    member_user_ids: List[int] = []
    chairman_user_id: Optional[int] = None