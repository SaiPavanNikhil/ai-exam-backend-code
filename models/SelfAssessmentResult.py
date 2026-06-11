from sqlalchemy import Column, Integer, Text, String, DateTime
from datetime import datetime
from database import Base

class SelfAssessmentResult(Base):
    __tablename__ = "self_assessment_results"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, nullable=False)

    assessment_id = Column(String(100), nullable=False, unique=True)

    course = Column(String(255), nullable=False)

    final_response = Column(Text, nullable=True)

    final_marks = Column(Integer, nullable=True)

    completed_at = Column(
        DateTime,
        default=datetime.utcnow
    )