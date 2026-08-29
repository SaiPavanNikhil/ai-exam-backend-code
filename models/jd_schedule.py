from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class JDSchedule(Base):
    __tablename__ = "jd_schedule"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jd_id = Column(Integer, nullable=False, index=True)      # no FK — job_descriptions untouched
    panel_id = Column(Integer, nullable=False, index=True)   # no FK — panels untouched
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    courses = relationship("JDScheduleCourse", back_populates="schedule", cascade="all, delete-orphan")


class JDScheduleCourse(Base):
    __tablename__ = "jd_schedule_courses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("jd_schedule.id"), nullable=False)
    course_id = Column(BigInteger, nullable=False, index=True)  # no FK — course_master untouched
    year = Column(String(50), nullable=False)

    schedule = relationship("JDSchedule", back_populates="courses")