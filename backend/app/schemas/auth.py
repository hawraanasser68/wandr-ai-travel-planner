"""
Auth schemas — validate what the API accepts and returns for registration/login.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    webhook_email: EmailStr | None = None  # optional: where to send trip summary emails

    @field_validator("password")
    @classmethod
    def password_not_trivial(cls, v: str) -> str:
        if v.lower() in {"password", "12345678", "password1"}:
            raise ValueError("Password is too common")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    webhook_email: EmailStr | None
    created_at: datetime

    model_config = {"from_attributes": True}  # allows .model_validate(orm_object)
