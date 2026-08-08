from fastapi import FastAPI
from app.database import SessionLocal
from app.models import User
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException


app = FastAPI()

class UserCreate(BaseModel):
    Email: str
    DisplayName: str
    AuthProvider: str

@app.get("/")
def home():
    return {"message": "SenseLens API is running"}


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
                "AuthProvider": user.AuthProvider
            }
            for user in users
        ]

    finally:
        session.close()


@app.post("/users")
def create_user(user_data: UserCreate):
    session = SessionLocal()

    try:
        existing_user = session.query(User).filter(
            User.Email == user_data.Email
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email already exists"
            )

        new_user = User(
            Email=user_data.Email,
            DisplayName=user_data.DisplayName,
            AuthProvider=user_data.AuthProvider
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        return {
            "UserID": str(new_user.UserID),
            "Email": new_user.Email,
            "DisplayName": new_user.DisplayName,
            "AuthProvider": new_user.AuthProvider
        }

    finally:
        session.close()