from pydantic import BaseModel

class ScheduleInterviewRequest(BaseModel):
    candidate_id: int
    interview_category: str
    interview_date: str
    start_time: str
    end_time: str
    interview_id: str

    panel_id: int | None = None

    panel_name: str | None = None
    chairman_user_id: int | None = None
    member_user_ids: list[int] = []