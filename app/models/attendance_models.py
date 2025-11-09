from sqlalchemy import Column, Integer, ForeignKey, Date, DateTime, Float, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum
from datetime import datetime, date

class StatusEnum(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"
    half_day = "half_day"

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, default=date.today)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    total_hours = Column(Float, default=0.0)
    status = Column(Enum(StatusEnum), default=StatusEnum.present)

    # Relationship to user table
    user = relationship("User")
