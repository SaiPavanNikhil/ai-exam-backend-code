from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Enum as SQLEnum
from database import Base
from datetime import datetime
from enum import Enum

# 1. Standalone definition of your 6 course categories
class CourseProgram(str, Enum):
    BBA = "BBA"
    MBA = "MBA"
    B_TECH = "B-Tech"
    MCA = "MCA"
    B_COM = "B.Com"
    M_COM = "M.Com"

class Question(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    expected_answer = Column(Text)
    category = Column(String)
    difficulty = Column(String)
    time_limit = Column(Integer, default=120)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Safely uses the CourseProgram enum defined right above it
    course = Column(SQLEnum(CourseProgram), index=True, nullable=False)