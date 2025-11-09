from typing import Optional
from pydantic import BaseModel


class SessionInfo(BaseModel):
    user_id: int
    device_id: Optional[str] = None
    device_location: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    session: SessionInfo


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str


class MessageResponse(BaseModel):
    message: str

