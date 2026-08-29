from sqlalchemy import Column, Integer, Text, String, DateTime
from datetime import datetime
from database import Base

class SelfAssessmentAnswer(Base):
    __tablename__ = "self_assessment_answers"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, nullable=False)

    # question_id = Column(Integer, nullable=False)

    started_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    answer_text = Column(Text, nullable=True)

    ai_response = Column(Text, nullable=True)

    ai_score = Column(Integer, nullable=True)

    status = Column(
        String(20),
        default="Processing"
    )

    assessment_id = Column(
        String(100),
        nullable=False,
        index=True
    )

    course = Column(String(100), nullable=True)

    question_text = Column(Text, nullable=False)

    expected_answer = Column(Text, nullable=True)