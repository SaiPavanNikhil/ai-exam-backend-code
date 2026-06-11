from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# ✅ Railway injects DATABASE_URL automatically
# ✅ Falls back to your local DB when running locally
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:S0ft%40321@localhost:5432/online_ai_test"
)

# ✅ Railway uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# from sqlalchemy.orm import sessionmaker

# import urllib.parse

# password = urllib.parse.quote_plus("S0ft@321")

# DATABASE_URL = f"postgresql://postgres:{password}@localhost:5432/online_ai_test"

# engine = create_engine(DATABASE_URL)

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()


# # Dependency (like @Autowired DB session)
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()