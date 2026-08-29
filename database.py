from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Load variables from .env when running locally
load_dotenv()


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Railway automatically provides DATABASE_URL when deployed.
database_url = os.getenv("DATABASE_URL")

# Railway also provides DATABASE_PUBLIC_URL.
# This is the URL that can be accessed from your local PC.
database_public_url = os.getenv("DATABASE_PUBLIC_URL")


# ============================================================
# HANDLE LOCAL CONNECTION TO RAILWAY
# ============================================================

if database_url and "postgres.railway.internal" in database_url:

    # We are currently getting Railway's internal URL.
    # That URL cannot be resolved from your local computer.
    #
    # If DATABASE_PUBLIC_URL is available, use that instead.

    if database_public_url:
        database_url = database_public_url


# ============================================================
# VALIDATE DATABASE URL
# ============================================================

if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Please set DATABASE_URL in Railway or .env"
    )


# ============================================================
# SQLALCHEMY URL COMPATIBILITY
# ============================================================

# Some Railway configurations may return postgres://
# SQLAlchemy expects postgresql://

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )


# ============================================================
# ENGINE
# ============================================================

engine = create_engine(
    database_url,
    pool_pre_ping=True
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================================
# BASE
# ============================================================

Base = declarative_base()


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()