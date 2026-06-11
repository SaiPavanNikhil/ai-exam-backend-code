from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

# 🌟 FIX 1: Import the centralized Base from your real database config file
from database import Base 
from models.question import CourseProgram

# 🌟 FIX 2: Removed "Base = declarative_base()" completely! 
# This ensures all tables below are tracked globally by the real database metadata.

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
    # 🌟 FIX 3: Updated to timezone-aware modern datetime standard
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    course_program = Column(String(100), nullable=False) 
    department_branch = Column(String(100), nullable=True) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    video_path = Column(String, nullable=False)


class Panel(Base):
    __tablename__ = "panels"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    panel_name = Column(String(100))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
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
    scheduled_at = Column(String(100))  
    status = Column(String(50), default="Scheduled")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    candidate = relationship("Candidate")
    panel = relationship("Panel", back_populates="interviews")

    video_path = Column(String, nullable=True)
    interview_category = Column(String, nullable=True)
    interview_id = Column(String(50), nullable=True)