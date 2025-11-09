from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.dependencies import get_db
from app.models.user_models import User, RoleEnum
from app.models.session_models import UserSession
from app.utils.jwt_handler import create_access_token, get_current_user, oauth2_scheme
from typing import Optional
from app.schemas.user import UserOut
from app.schemas.auth import TokenResponse, RefreshResponse, MessageResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

"""Database session dependency is provided by app.dependencies.get_db"""

# app/routes/auth_routes.py



class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str
    location: str
    picture: Optional[str] = None
    date_of_birth: Optional[date] = None
    joined_date: Optional[date] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = True


@router.post("/register", response_model=MessageResponse)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed_pw = pwd_context.hash(request.password)
    # Coerce role to RoleEnum; raises ValueError if invalid
    try:
        role_value = RoleEnum(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = User(
        name=request.name,
        email=request.email,
        password_hash=hashed_pw,
        role=role_value,
        location=request.location,
        picture=request.picture,
        date_of_birth=request.date_of_birth,
        joined_date=request.joined_date,
        manager_id=request.manager_id,
        is_active=(True if request.is_active is None else request.is_active),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": f"User {request.name} registered successfully"}

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    device_id: Optional[str] = Query(None, description="Client device identifier"),
    device_location: Optional[str] = Query(None, description="Client device location (human readable)"),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    if not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Build JWT payload from the user instance, not the class
    payload = {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "location": user.location,
    }

    # Weekly expiry (7 days)
    token = create_access_token(payload, expires_minutes=7 * 24 * 60)

    # Persist login session with device info
    session = UserSession(
        user_id=user.id,
        device_id=device_id,
        device_location=device_location,
        token=token,
        is_active=1,
    )
    db.add(session)
    db.commit()
    # Return role as string for clients
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role_str,
        "session": {
            "user_id": user.id,
            "device_id": device_id,
            "device_location": device_location,
        },
    }


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id, UserSession.token == token, UserSession.is_active == 1)
        .first()
    )
    if session:
        session.is_active = 0
        db.commit()
    # Redirect to API docs as a "login page" placeholder; adjust for your frontend
    return RedirectResponse(url="/docs", status_code=307)


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id, UserSession.token == token, UserSession.is_active == 1)
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Session not found or inactive")

    payload = {
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        "location": current_user.location,
    }
    new_token = create_access_token(payload, expires_minutes=7 * 24 * 60)
    session.token = new_token
    session.login_time = datetime.utcnow()
    db.commit()
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": role_str,
        "location": current_user.location,
        "picture": current_user.picture,
        "date_of_birth": current_user.date_of_birth,
        "joined_date": current_user.joined_date,
        "manager_id": current_user.manager_id,
        "is_active": current_user.is_active,
    }
