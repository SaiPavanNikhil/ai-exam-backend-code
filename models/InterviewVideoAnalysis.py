from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from sqlalchemy.sql import func
from database import Base


class InterviewVideoAnalysis(Base):
    __tablename__ = "interview_video_analysis"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)

    interview_id = Column(String(100), nullable=False)

    candidate_id = Column(Integer, nullable=False)

    interview_mode = Column(String(20), nullable=False)

    video = Column(String(255))

    dominant_emotion = Column(String(50))

    total_analyzed_frames = Column(Integer)

    happy_frames = Column(Integer)

    neutral_frames = Column(Integer)

    sad_frames = Column(Integer)

    angry_frames = Column(Integer)

    fear_frames = Column(Integer)

    disgust_frames = Column(Integer)

    surprise_frames = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())