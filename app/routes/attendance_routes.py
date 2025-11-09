from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List

from app.models.attendance_models import Attendance, StatusEnum
from app.models.user_models import User, RoleEnum
from app.utils.jwt_handler import get_current_user
from app.dependencies import get_db
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate, AttendanceOut

router = APIRouter(prefix="/attendance", tags=["Attendance"])


"""Schemas moved to app.schemas.attendance"""


# ==========================
# Helpers
# ==========================
def is_manager(user: User) -> bool:
    return user.role in {RoleEnum.project_manager, RoleEnum.supervisor}


def _compute_display_status(record: Attendance, today: date) -> StatusEnum:
    computed = record.status
    if record.date < today:
        if record.check_in is None:
            computed = StatusEnum.absent
        elif record.check_out is None:
            computed = StatusEnum.half_day
    return computed


# ==========================
# Check-In / Check-Out / History
# ==========================
@router.post("/checkin")
def check_in(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    existing = (
        db.query(Attendance)
        .filter(Attendance.user_id == current_user.id, Attendance.date == today)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already checked in today.")

    record = Attendance(
        user_id=current_user.id,
        date=today,
        check_in=datetime.utcnow(),
        status=StatusEnum.present,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": f"{current_user.name} checked in successfully", "time": record.check_in}


@router.post("/checkout")
def check_out(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    record = (
        db.query(Attendance)
        .filter(Attendance.user_id == current_user.id, Attendance.date == today)
        .first()
    )

    if not record or not record.check_in:
        raise HTTPException(status_code=400, detail="No check-in record found.")
    if record.check_out:
        raise HTTPException(status_code=400, detail="Already checked out today.")

    now = datetime.utcnow()
    if now <= record.check_in:
        raise HTTPException(status_code=400, detail="Checkout time must be after check-in.")

    record.check_out = now
    record.total_hours = (record.check_out - record.check_in).total_seconds() / 3600
    db.commit()
    db.refresh(record)
    return {
        "message": f"{current_user.name} checked out successfully",
        "total_hours": round(record.total_hours or 0, 2),
    }


@router.get("/history", response_model=List[AttendanceOut])
def get_attendance_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = (
        db.query(Attendance)
        .filter(Attendance.user_id == current_user.id)
        .order_by(Attendance.date.desc())
    )
    records = q.offset(offset).limit(limit).all()
    today = date.today()
    result: List[AttendanceOut] = []
    for r in records:
        computed_status = r.status
        if r.date < today:
            if r.check_in is None:
                computed_status = StatusEnum.absent
            elif r.check_out is None:
                computed_status = StatusEnum.half_day
        # For today with no checkout, keep present (in-progress)
        result.append(
            {
                "id": r.id,
                "user_id": r.user_id,
                "date": r.date,
                "check_in": r.check_in,
                "check_out": r.check_out,
                "total_hours": r.total_hours,
                "status": computed_status,
            }
        )
    return result


# ==========================
# CRUD Endpoints
# ==========================
@router.post("/", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def create_attendance(
    payload: AttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Default user_id to current user unless a manager sets it
    target_user_id = payload.user_id or current_user.id
    if payload.user_id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Not allowed to create for another user")

    target_date = payload.date or date.today()
    exists = (
        db.query(Attendance)
        .filter(Attendance.user_id == target_user_id, Attendance.date == target_date)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Attendance record already exists for date")

    record = Attendance(
        user_id=target_user_id,
        date=target_date,
        check_in=payload.check_in,
        check_out=payload.check_out,
        status=payload.status or StatusEnum.present,
    )
    # Validate time order if both provided
    if record.check_in and record.check_out and record.check_out <= record.check_in:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")
    if record.check_in and record.check_out:
        record.total_hours = (record.check_out - record.check_in).total_seconds() / 3600
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[AttendanceOut])
def list_attendance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(None, description="Filter by user id (manager only)"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status_filter: Optional[StatusEnum] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    asc: bool = Query(False, description="Sort by date ascending if true"),
):
    q = db.query(Attendance)
    if user_id is not None:
        if not is_manager(current_user) and user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not allowed to view other users")
        q = q.filter(Attendance.user_id == user_id)
    else:
        q = q.filter(Attendance.user_id == current_user.id)

    if start_date:
        q = q.filter(Attendance.date >= start_date)
    if end_date:
        q = q.filter(Attendance.date <= end_date)
    if status_filter is not None:
        q = q.filter(Attendance.status == status_filter)

    q = q.order_by(Attendance.date.asc() if asc else Attendance.date.desc())
    records = q.offset(offset).limit(limit).all()
    today = date.today()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "date": r.date,
            "check_in": r.check_in,
            "check_out": r.check_out,
            "total_hours": r.total_hours,
            "status": _compute_display_status(r, today),
        }
        for r in records
    ]


@router.get("/{attendance_id}", response_model=AttendanceOut)
def get_attendance(
    attendance_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance not found")
    if not is_manager(current_user) and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this record")
    today = date.today()
    return {
        "id": record.id,
        "user_id": record.user_id,
        "date": record.date,
        "check_in": record.check_in,
        "check_out": record.check_out,
        "total_hours": record.total_hours,
        "status": _compute_display_status(record, today),
    }


@router.put("/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance not found")
    # Only managers can update attendance records
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Only managers can update attendance records")

    if payload.date is not None:
        # Prevent duplicate date for same user when changing date
        duplicate = (
            db.query(Attendance)
            .filter(
                Attendance.user_id == record.user_id,
                Attendance.date == payload.date,
                Attendance.id != record.id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Another record already exists for that date")
        record.date = payload.date
    if payload.check_in is not None:
        record.check_in = payload.check_in
    if payload.check_out is not None:
        record.check_out = payload.check_out
    if payload.status is not None:
        record.status = payload.status

    if record.check_in and record.check_out:
        if record.check_out <= record.check_in:
            raise HTTPException(status_code=400, detail="check_out must be after check_in")
        record.total_hours = (record.check_out - record.check_in).total_seconds() / 3600

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance not found")
    # Only managers can delete attendance records
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Only managers can delete attendance records")

    db.delete(record)
    db.commit()
    return None
