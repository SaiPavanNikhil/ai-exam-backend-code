from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.JobDescription import JobDescription
from models.course_master import CourseMaster
from models.model import Panel, PanelMember
from models.jd_schedule import JDSchedule, JDScheduleCourse
from schemas.jd_schedule import (
    JobDescriptionOut, CourseMasterOut,
    JDScheduleCreate, JDScheduleOut
)

router = APIRouter(prefix="/api", tags=["jd-schedule"])


@router.get("/job-descriptions", response_model=List[JobDescriptionOut])
def list_job_descriptions(db: Session = Depends(get_db)):
    return db.query(JobDescription).all()


@router.get("/course-master", response_model=List[CourseMasterOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(CourseMaster).all()


@router.post("/jd-schedule", response_model=JDScheduleOut)
def create_jd_schedule(payload: JDScheduleCreate, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.id == payload.jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")

    if not payload.eligibility:
        raise HTTPException(status_code=400, detail="At least one eligibility row is required")

    # ---------------------------------------
    # Resolve panel: existing or newly created
    # ---------------------------------------
    panel_id = payload.panel_id

    if panel_id is None:
        if not payload.panel_name or not payload.member_user_ids:
            raise HTTPException(
                status_code=400,
                detail="Provide either panel_id, or panel_name + member_user_ids to create a new panel"
            )

        panel = Panel(panel_name=payload.panel_name, created_by=1)
        db.add(panel)
        db.commit()
        db.refresh(panel)

        for user_id in payload.member_user_ids:
            role = "chairman" if user_id == payload.chairman_user_id else "member"
            db.add(PanelMember(panel_id=panel.id, user_id=user_id, role=role))
        db.commit()

        panel_id = panel.id
    else:
        panel = db.query(Panel).filter(Panel.id == panel_id).first()
        if not panel:
            raise HTTPException(status_code=404, detail="Selected panel not found")

    # ---------------------------------------
    # Create schedule + eligibility rows
    # ---------------------------------------
    schedule = JDSchedule(jd_id=payload.jd_id, panel_id=panel_id)
    db.add(schedule)
    db.flush()

    for item in payload.eligibility:
        db.add(JDScheduleCourse(
            schedule_id=schedule.id,
            course_id=item.course_id,
            year=item.year
        ))

    db.commit()
    db.refresh(schedule)
    return schedule