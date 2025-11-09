# models/session_models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(String, nullable=True)   # phone ID or browser fingerprint
    device_location = Column(String, nullable=True)  # human-readable device location
    token = Column(String, nullable=False)
    login_time = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)
