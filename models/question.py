# from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Enum as SQLEnum
# from database import Base
# from datetime import datetime
# from enum import Enum

# # 1. Standalone definition of your 6 course categories
# class CourseProgram(str, Enum):
#     BBA = "BBA"
#     MBA = "MBA"
#     B_TECH = "B-Tech"
#     MCA = "MCA"
#     B_COM = "B.Com"
#     M_COM = "M.Com"

# class Question(Base):
#     __tablename__ = "question_bank"

#     id = Column(Integer, primary_key=True, index=True)
#     question_text = Column(Text, nullable=False)
#     expected_answer = Column(Text)
#     category = Column(String)
#     difficulty = Column(String)
#     time_limit = Column(Integer, default=120)
#     created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
#     # Safely uses the CourseProgram enum defined right above it
#     course = Column(SQLEnum(CourseProgram), index=True, nullable=False)

from sqlalchemy import Column, Integer, BigInteger, String, Text, TIMESTAMP, ForeignKey, Enum as SQLEnum
from database import Base
from datetime import datetime
from enum import Enum
from models.subject_master import SubjectMaster

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

    # New: link questions to the dynamic course_master / subject_master tables
    course_id = Column(BigInteger, ForeignKey("course_master.course_id"), nullable=True, index=True)
    subject_id = Column(Integer, ForeignKey("subject_master.subject_id"), nullable=True, index=True)