from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user_models import User, RoleEnum


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    role: str,
    location: Optional[str] = None,
    picture: Optional[str] = None,
    date_of_birth=None,
    joined_date=None,
    manager_id: Optional[int] = None,
    is_active: bool = True,
) -> User:
    if db.query(User).filter(User.email == email).first():
        raise ValueError("Email already exists")
    try:
        role_value = RoleEnum(role)
    except ValueError:
        raise ValueError("Invalid role")

    hashed_pw = pwd_context.hash(password)
    user = User(
        name=name,
        email=email,
        password_hash=hashed_pw,
        role=role_value,
        location=location,
        picture=picture,
        date_of_birth=date_of_birth,
        joined_date=joined_date,
        manager_id=manager_id,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_with_manager_validation(
    db: Session,
    *,
    current_manager_id: int,
    name: str,
    email: str,
    password: str,
    role: str,
    location: Optional[str] = None,
    picture: Optional[str] = None,
    date_of_birth=None,
    joined_date=None,
    manager_id: Optional[int] = None,
    is_active: Optional[bool] = True,
) -> User:
    # determine manager
    target_manager_id = manager_id or current_manager_id
    manager = db.query(User).filter(User.id == target_manager_id).first()
    if not manager or manager.role not in {RoleEnum.project_manager, RoleEnum.supervisor}:
        raise ValueError("Manager must be a valid manager/supervisor")
    if email and db.query(User).filter(User.email == email).first():
        raise ValueError("Email already exists")
    try:
        role_value = RoleEnum(role)
    except ValueError:
        raise ValueError("Invalid role")

    hashed_pw = pwd_context.hash(password)
    user = User(
        name=name,
        email=email,
        password_hash=hashed_pw,
        role=role_value,
        location=location,
        picture=picture,
        date_of_birth=date_of_birth,
        joined_date=joined_date,
        manager_id=target_manager_id,
        is_active=True if is_active is None else is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_with_validation(
    db: Session,
    *,
    acting_user_id: int,
    user_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    picture: Optional[str] = None,
    date_of_birth=None,
    joined_date=None,
    manager_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    if name is not None:
        user.name = name
    if email is not None:
        existing = db.query(User).filter(User.email == email, User.id != user.id).first()
        if existing:
            raise ValueError("Email already in use")
        user.email = email
    if role is not None:
        try:
            user.role = RoleEnum(role)
        except ValueError:
            raise ValueError("Invalid role")
    if location is not None:
        user.location = location
    if picture is not None:
        user.picture = picture
    if date_of_birth is not None:
        user.date_of_birth = date_of_birth
    if joined_date is not None:
        user.joined_date = joined_date
    if manager_id is not None:
        if manager_id == user.id:
            raise ValueError("User cannot be their own manager")
        manager = db.query(User).filter(User.id == manager_id).first()
        if not manager or manager.role not in {RoleEnum.project_manager, RoleEnum.supervisor}:
            raise ValueError("Assigned manager must have manager/supervisor role")
        user.manager_id = manager_id
    if is_active is not None:
        if user.id == acting_user_id and is_active is False:
            raise ValueError("You cannot deactivate your own account")
        user.is_active = is_active

    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    *,
    user_id: int,
    picture: Optional[str] = None,
    date_of_birth=None,
    joined_date=None,
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    if picture is not None:
        user.picture = picture
    if date_of_birth is not None:
        user.date_of_birth = date_of_birth
    if joined_date is not None:
        user.joined_date = joined_date
    db.commit()
    db.refresh(user)
    return user


def assign_manager(
    db: Session,
    *,
    employee_id: int,
    manager_id: int,
) -> User:
    employee = db.query(User).filter(User.id == employee_id).first()
    if not employee:
        raise ValueError("User not found")
    manager = db.query(User).filter(User.id == manager_id).first()
    if not manager:
        raise ValueError("Manager not found")
    if manager.role not in {RoleEnum.project_manager, RoleEnum.supervisor}:
        raise ValueError("Assigned manager must have manager/supervisor role")
    if manager.id == employee.id:
        raise ValueError("User cannot be their own manager")
    employee.manager_id = manager.id
    db.commit()
    db.refresh(employee)
    return employee


def set_active_status(
    db: Session,
    *,
    acting_user_id: int,
    user_id: int,
    active: bool,
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    if user.id == acting_user_id and active is False:
        raise ValueError("You cannot deactivate your own account")
    user.is_active = active
    db.commit()
    db.refresh(user)
    return user


def list_team(
    db: Session,
    *,
    manager_id: int,
    limit: int = 50,
    offset: int = 0,
):
    return (
        db.query(User)
        .filter(User.manager_id == manager_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


def list_users_for_manager(
    db: Session,
    *,
    manager_id: int,
    include_inactive: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    q = db.query(User).filter(User.manager_id == manager_id)
    if not include_inactive:
        q = q.filter(User.is_active == True)  # noqa: E712
    return q.offset(offset).limit(limit).all()


def get_user_for_manager(
    db: Session,
    *,
    manager_id: int,
    user_id: int,
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    if user.manager_id != manager_id:
        # signal a forbidden access for non-team member
        raise PermissionError("User is not in your team")
    return user
