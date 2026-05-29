from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import sessionmaker

import urllib.parse

password = urllib.parse.quote_plus("S0ft@321")

DATABASE_URL = f"postgresql://postgres:{password}@localhost:5432/online_ai_test"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency (like @Autowired DB session)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()