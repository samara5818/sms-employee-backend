from sqlalchemy import Column, String, Enum, Integer, Date, ForeignKey, Boolean
from app.database import Base
import enum

class RoleEnum(str, enum.Enum):
    project_manager = "project_manager"
    supervisor = "supervisor"
    driver = "driver"
    delivery_associate = "delivery_associate"
    sweeper = "sweeper"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.driver)
    location = Column(String, nullable=True)
    picture = Column(String, nullable=True)  # URL or path to profile picture
    date_of_birth = Column(Date, nullable=True)
    joined_date = Column(Date, nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
