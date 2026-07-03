from sqlalchemy import Column, Integer, String
from database import Base

class SubjectMaster(Base):
    __tablename__ = "subject_master"
    __table_args__ = {'extend_existing': True}

    subject_id = Column(Integer, primary_key=True, index=True)
    subject_code = Column(String, nullable=True)
    subject_name = Column(String, nullable=True)