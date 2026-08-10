import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import User

from app.routers.cbd_status import router as cbd_status_router
from app.routers.preferences import router as preferences_router
from app.routers.pedestrian import router as pedestrian_router
from app.routers.refuges import router as refuges_router
from app.routers.saved_routes import router as saved_routes_router
from app.routers.routes import router as routes_router


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="SenseLens Backend API",
    description="Backend API for the SenseLens Industry Experience Project",
    version="1.0.0",
)


# ============================================================
# CORS Configuration
# ============================================================
#
# Allows the deployed Vue frontend and local Vue development
# server to communicate with this FastAPI backend.
#
# Production frontend:
# https://senselens.onrender.com
#

origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGIN",
        (
            "https://senselens.onrender.com,"
            "https://senselense-duk4.onrender.com,"
            "http://localhost:5173,"
            "http://127.0.0.1:5173"
        ),
    ).split(",")
    if origin.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API Routers
# ============================================================

app.include_router(
    cbd_status_router,
    tags=["CBD Status"],
)

app.include_router(
    preferences_router,
    tags=["User Preferences"],
)

app.include_router(
    pedestrian_router,
    tags=["Pedestrian Data"],
)

app.include_router(
    refuges_router,
    tags=["Refuges"],
)

app.include_router(
    saved_routes_router,
    tags=["Saved Routes"],
)

app.include_router(
    routes_router,
    tags=["Routes"],
)


# ============================================================
# User Request Model
# ============================================================

class UserCreate(BaseModel):
    Email: str
    DisplayName: str
    AuthProvider: str


# ============================================================
# Root Endpoint
# ============================================================

@app.get("/")
def home():
    return {
        "application": "SenseLens Backend API",
        "version": "1.0.0",
        "status": "running",
    }


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# ============================================================
# Users
# ============================================================

@app.get("/users")
def get_users():
    session = SessionLocal()

    try:
        users = session.query(User).all()

        return [
            {
                "UserID": str(user.UserID),
                "Email": user.Email,
                "DisplayName": user.DisplayName,
                "AuthProvider": user.AuthProvider,
            }
            for user in users
        ]

    finally:
        session.close()


@app.post("/users")
def create_user(user_data: UserCreate):
    session = SessionLocal()

    try:
        existing_user = (
            session.query(User)
            .filter(User.Email == user_data.Email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email already exists",
            )

        new_user = User(
            Email=user_data.Email,
            DisplayName=user_data.DisplayName,
            AuthProvider=user_data.AuthProvider,
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        return {
            "UserID": str(new_user.UserID),
            "Email": new_user.Email,
            "DisplayName": new_user.DisplayName,
            "AuthProvider": new_user.AuthProvider,
        }

    except HTTPException:
        session.rollback()
        raise

    except Exception as error:
        session.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create user",
        ) from error

    finally:
        session.close()
