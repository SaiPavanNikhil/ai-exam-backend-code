from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50))

    designation = Column(String(100))   # ✅ ADD THIS

    created_at = Column(DateTime, default=datetime.utcnow)  # ✅ ADD THIS
    member_type = Column(String, nullable=True)