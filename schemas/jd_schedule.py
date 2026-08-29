from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobDescriptionOut(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class CourseMasterOut(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    branch_name: str

    class Config:
        from_attributes = True


class EligibilityItem(BaseModel):
    course_id: int
    year: str


class JDScheduleCreate(BaseModel):
    jd_id: int
    eligibility: List[EligibilityItem]

    # Panel — either use an existing one, or create a new one inline
    panel_id: Optional[int] = None
    panel_name: Optional[str] = None
    chairman_user_id: Optional[int] = None
    member_user_ids: Optional[List[int]] = None


class JDScheduleOut(BaseModel):
    id: int
    jd_id: int
    panel_id: int
    created_at: datetime

    class Config:
        from_attributes = True