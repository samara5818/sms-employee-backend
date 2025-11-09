from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel
from app.models.attendance_models import StatusEnum


class AttendanceBase(BaseModel):
    date: Optional[date] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[StatusEnum] = None


class AttendanceCreate(AttendanceBase):
    user_id: Optional[int] = None


class AttendanceUpdate(BaseModel):
    date: Optional[date] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[StatusEnum] = None


class AttendanceOut(BaseModel):
    id: int
    user_id: int
    date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    total_hours: Optional[float]
    status: Optional[StatusEnum]

    class Config:
        from_attributes = True

