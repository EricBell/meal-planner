from sqlmodel import create_engine, Session, SQLModel
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meal_planner.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Create a new database session. Caller is responsible for commit/close."""
    return Session(engine)


def get_session_sync() -> Session:
    """For use in background scheduler jobs."""
    return Session(engine)