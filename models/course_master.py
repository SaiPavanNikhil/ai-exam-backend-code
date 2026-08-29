from sqlalchemy import Column, Integer, String
from database import Base


class CourseMaster(Base):
    __tablename__ = "course_master"

    course_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_code = Column(String, unique=True, index=True, nullable=False)
    course_name = Column(String, nullable=False)
    branch_name = Column(String, nullable=True)