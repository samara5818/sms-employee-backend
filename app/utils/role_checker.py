# app/utils/role_checker.py
from fastapi import Depends, HTTPException, status
from app.utils.jwt_handler import get_current_user

def role_required(*allowed_roles):
    def decorator(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {current_user.role}",
            )
        return current_user
    return decorator
