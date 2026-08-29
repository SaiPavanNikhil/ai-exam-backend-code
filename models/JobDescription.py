from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone

from database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    title = Column(
        String(255),
        nullable=False
    )

    pdf_filename = Column(
        String(255),
        nullable=False
    )

    pdf_path = Column(
        String(255),
        nullable=False
    )

    keywords = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )