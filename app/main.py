from fastapi import FastAPI
from app.database import Base, engine
from app.routes import auth_routes, attendance_routes
from app.routes import admin_routes

app = FastAPI(title="Attendance App with Auth")

app.include_router(auth_routes.router)
app.include_router(attendance_routes.router)
app.include_router(admin_routes.router)


@app.get("/")
def home():
    return {"message": "Authentication system ready 🚀"}
