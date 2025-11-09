# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Connect to PostgreSQL (make sure DATABASE_URL is correct in .env)
engine = create_engine(settings.DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()

try:
    # Replace these lines with your actual model module names
    from app.models import user_models, attendance_models
except ModuleNotFoundError as e:
    print("⚠️ Warning: Could not import models.", e)
