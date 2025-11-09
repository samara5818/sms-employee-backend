from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Path, status, Query
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user_models import User, RoleEnum
from app.utils.jwt_handler import get_current_user
from app.dependencies import get_db
from app.utils.role_checker import role_required
from app.schemas.user import (
    UserProfileUpdate,
    AssignManagerRequest,
    UserCreate,
    UserUpdate,
    UserOut,
)
from app.services.user_service import (
    create_user_with_manager_validation,
    update_user_with_validation,
    update_user_profile as update_user_profile_service,
    assign_manager as assign_manager_service,
    set_active_status,
    list_team as list_team_service,
    list_users_for_manager as list_users_for_manager_service,
    get_user_for_manager as get_user_for_manager_service,
)

router = APIRouter(prefix="/users", tags=["Users (Admin)"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")




def _is_in_team(manager: User, employee: User) -> bool:
    return employee.manager_id == manager.id


@router.put("/{user_id}/profile", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_user_profile(
    user_id: int = Path(..., gt=0),
    payload: UserProfileUpdate = None,
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Managers/supervisors can only update their team members
    if not _is_in_team(current_user, user):
        raise HTTPException(status_code=403, detail="User is not in your team")
    try:
        user = update_user_profile_service(
            db,
            user_id=user_id,
            picture=payload.picture,
            date_of_birth=payload.date_of_birth,
            joined_date=payload.joined_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "location": user.location,
        "picture": user.picture,
        "date_of_birth": user.date_of_birth,
        "joined_date": user.joined_date,
        "manager_id": user.manager_id,
        "is_active": user.is_active,
    }


@router.put("/{user_id}/manager", status_code=status.HTTP_200_OK)
def assign_manager(
    user_id: int = Path(..., gt=0),
    payload: AssignManagerRequest = None,
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
):
    employee = db.query(User).filter(User.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="User not found")
    if not _is_in_team(current_user, employee):
        raise HTTPException(status_code=403, detail="User is not in your team")
    try:
        employee = assign_manager_service(db, employee_id=user_id, manager_id=payload.manager_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Assigned user {employee.id} to manager {employee.manager_id}"}


@router.get("/team", response_model=List[UserOut], status_code=status.HTTP_200_OK)
def list_my_team(
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    team = list_team_service(db, manager_id=current_user.id, limit=limit, offset=offset)
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "location": u.location,
            "picture": u.picture,
            "date_of_birth": u.date_of_birth,
            "joined_date": u.joined_date,
            "manager_id": u.manager_id,
            "is_active": u.is_active,
        }
        for u in team
    ]


@router.get("/", response_model=List[UserOut], status_code=status.HTTP_200_OK)
def list_users(
    include_inactive: bool = Query(False, description="Include inactive users"),
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    users = list_users_for_manager_service(
        db,
        manager_id=current_user.id,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "location": u.location,
            "picture": u.picture,
            "date_of_birth": u.date_of_birth,
            "joined_date": u.joined_date,
            "manager_id": u.manager_id,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
):
    try:
        user = create_user_with_manager_validation(
            db,
            current_manager_id=current_user.id,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            location=payload.location,
            picture=payload.picture,
            date_of_birth=payload.date_of_birth,
            joined_date=payload.joined_date,
            manager_id=payload.manager_id,
            is_active=payload.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "location": user.location,
        "picture": user.picture,
        "date_of_birth": user.date_of_birth,
        "joined_date": user.joined_date,
        "manager_id": user.manager_id,
        "is_active": user.is_active,
    }


@router.put("/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_user(
    user_id: int = Path(..., gt=0),
    payload: UserUpdate = None,
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _is_in_team(current_user, user):
        raise HTTPException(status_code=403, detail="User is not in your team")
    try:
        user = update_user_with_validation(
            db,
            acting_user_id=current_user.id,
            user_id=user_id,
            name=payload.name,
            email=payload.email,
            role=payload.role,
            location=payload.location,
            picture=payload.picture,
            date_of_birth=payload.date_of_birth,
            joined_date=payload.joined_date,
            manager_id=payload.manager_id,
            is_active=payload.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "location": user.location,
        "picture": user.picture,
        "date_of_birth": user.date_of_birth,
        "joined_date": user.joined_date,
        "manager_id": user.manager_id,
        "is_active": user.is_active,
    }


@router.get("/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int = Path(..., gt=0),
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
):
    try:
        user = get_user_for_manager_service(db, manager_id=current_user.id, user_id=user_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="User is not in your team")
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "location": user.location,
        "picture": user.picture,
        "date_of_birth": user.date_of_birth,
        "joined_date": user.joined_date,
        "manager_id": user.manager_id,
        "is_active": user.is_active,
    }


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def deactivate_user(
    user_id: int = Path(..., gt=0),
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _is_in_team(current_user, user):
        raise HTTPException(status_code=403, detail="User is not in your team")
    if not user.is_active:
        return {"message": "User already deactivated"}
    try:
        user = set_active_status(db, acting_user_id=current_user.id, user_id=user_id, active=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"User {user.id} deactivated"}


@router.post("/{user_id}/activate", status_code=status.HTTP_200_OK)
def activate_user(
    user_id: int = Path(..., gt=0),
    current_user: User = Depends(role_required(RoleEnum.project_manager, RoleEnum.supervisor)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _is_in_team(current_user, user):
        raise HTTPException(status_code=403, detail="User is not in your team")
    if user.is_active:
        return {"message": "User already active"}
    try:
        user = set_active_status(db, acting_user_id=current_user.id, user_id=user_id, active=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"User {user.id} activated"}
