import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Allow overriding DB connection in production while keeping a local default.
# Use /tmp/ for Cloud Run compatibility (read-only root filesystem)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/ustaad.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Create the SQLAlchemy engine. 
# check_same_thread=False is needed for SQLite to handle multi-threaded requests in FastAPI.
engine = create_engine(
    DATABASE_URL, connect_args=connect_args
)

# Create a SessionLocal class for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for the SQLAlchemy models
Base = declarative_base()

# Dependency for FastAPI to get DB sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
