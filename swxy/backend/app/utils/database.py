from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL


engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    # FastAPI's test client may open and close one SQLite connection on
    # different worker threads. PostgreSQL does not need this option.
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
