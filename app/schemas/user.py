from datetime import date
from typing import Optional

from pydantic import BaseModel


class UserProfileUpdate(BaseModel):
    picture: Optional[str] = None
    date_of_birth: Optional[date] = None
    joined_date: Optional[date] = None


class AssignManagerRequest(BaseModel):
    manager_id: int


class UserCreate(BaseModel):
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


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    picture: Optional[str] = None
    date_of_birth: Optional[date] = None
    joined_date: Optional[date] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    location: Optional[str] = None
    picture: Optional[str] = None
    date_of_birth: Optional[date] = None
    joined_date: Optional[date] = None
    manager_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True

