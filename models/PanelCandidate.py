from sqlalchemy import BigInteger, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from database import Base 


class PanelCandidate(Base):
    __tablename__ = "panel_candidates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    panel_id = Column(
        Integer,
        ForeignKey("panels.id"),
        nullable=False
    )

    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id"),
        nullable=False
    )

    interview_id = Column(
        String(50),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    panel = relationship("Panel")

    candidate = relationship("Candidate")