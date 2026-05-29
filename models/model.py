from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from models.question import CourseProgram

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50))
    designation = Column(String(100))
    member_type = Column(String(50))  # chairman / member
    created_at = Column(DateTime, default=datetime.utcnow)

class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(150))
    phone = Column(String(20))
    interview_id = Column(String(50), unique=True)
    
    # Student details
    student_father_mother_name = Column(String(200))
    student_dob = Column(String(50))
    student_gender = Column(String(20))
    student_category = Column(String(50))
    student_alt_mobile = Column(String(15))
    student_current_address = Column(Text)
    student_permanent_address = Column(Text)
    student_course_program = Column(String(200))
    student_department_branch = Column(String(200))
    student_university = Column(String(300))
    student_enrollment_no = Column(String(100))
    student_academic_year = Column(String(100))
    student_cgpa = Column(String(50))
    student_skills = Column(Text)
    student_certifications = Column(Text)
    student_projects = Column(Text)
    student_experience = Column(Text)
    student_strengths = Column(Text)
    student_weaknesses = Column(Text)
    student_career_objective = Column(Text)
    student_declaration = Column(Boolean, default=False)
    
    # File names
    photo_filename = Column(String(300))
    resume_filename = Column(String(300))
    idproof_filename = Column(String(300))
    certificates_filename = Column(String(300))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    video_path = Column(String, nullable=True)
    course_program = Column(SQLEnum(CourseProgram), index=True, nullable=True)

class Panel(Base):
    __tablename__ = "panels"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    panel_name = Column(String(100))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    members = relationship("PanelMember", back_populates="panel")
    interviews = relationship("Interview", back_populates="panel")

class PanelMember(Base):
    __tablename__ = "panel_members"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    panel_id = Column(Integer, ForeignKey("panels.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(50))  # chairman / member
    
    # Legacy fields for backward compatibility
    member_code = Column(String(50))
    member_name = Column(String(200))
    designation = Column(String(100))
    department = Column(String(100))
    organization = Column(String(200))
    experience = Column(Integer)
    mobile = Column(String(15))
    email = Column(String(150))
    expertise = Column(String(200))
    
    # Relationships
    panel = relationship("Panel", back_populates="members")
    user = relationship("User")

class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    panel_id = Column(Integer, ForeignKey("panels.id"))
    scheduled_at = Column(String(100))  # You might want to change this to DateTime
    status = Column(String(50), default="Scheduled")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate")
    panel = relationship("Panel", back_populates="interviews")

    video_path = Column(String, nullable=True)
    interview_category = Column(String, nullable=True)
    interview_id = Column(String(50), nullable=True)
