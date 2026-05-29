from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from database import Base
from datetime import datetime

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer)

    # 🔥 NEW (IMPORTANT)
    interview_id =Column(Integer, index=True)

    question_id = Column(Integer, ForeignKey("question_bank.id"))

    answer_text = Column(Text)

    time_taken = Column(Integer)

    # 🔥 NEW (OPTIONAL BUT RECOMMENDED)
    start_time = Column(Integer)  # ms
    end_time = Column(Integer)    # ms

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # 🔥 per-question video segment
    # recording_path = Column(String, nullable=True)

    panel_id = Column(Integer)

    score = Column(Integer)  

    ai_response = Column(Text, nullable=True) # Detailed feedback from Gemini
    ai_score = Column(Integer, nullable=True)   # Numerical score (0-10 or 0-100)