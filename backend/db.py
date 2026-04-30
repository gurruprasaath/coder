import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Vercel serverless filesystem is read-only except for /tmp.
# Use /tmp when running on Vercel, otherwise keep local ./app.db.
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    if os.environ.get("VERCEL"):
        SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/app.db"
    else:
        SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# connect_args={"check_same_thread": False} is needed only for SQLite.
connect_args = None
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args or {})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
