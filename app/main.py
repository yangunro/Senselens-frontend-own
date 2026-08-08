from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import User
from app.routers.cbd_status import router as cbd_status_router
from app.routers.preferences import router as preferences_router
from app.routers.saved_routes import router as saved_routes_router
from app.routers.refuges import router as refuges_router
from app.routers.routes import router as routes_router



app = FastAPI(
    title="SenseLens Backend API",
    description="Backend API for the SenseLens Industry Experience Project",
    version="1.0.0",
)


# Allow the Vue frontend to call the backend during development.
# Later, replace "*" with the deployed Vue frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(
    cbd_status_router,
    tags=["CBD Status"],
)
# Preferences router is registered after the CBD status router to ensure that the /preferences endpoint is accessible.
app.include_router(
    preferences_router,
    tags=["User Preferences"],
)
# Register the refuges router to handle refuge-related endpoints.
app.include_router(
    refuges_router,
    tags=["Refuges"],
)
# Register the saved routes router to handle saved route-related endpoints.
app.include_router(
    saved_routes_router,
    tags=["Saved Routes"],
)
# Register the routes router to handle route-related endpoints.
app.include_router(
    routes_router,
    tags=["Routes"],
)


class UserCreate(BaseModel):
    Email: str
    DisplayName: str
    AuthProvider: str


@app.get("/")
def home():
    return {
        "message": "SenseLens API is running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


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

    finally:
        session.close()