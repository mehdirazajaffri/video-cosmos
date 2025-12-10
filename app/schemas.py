# app/schemas.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ========== USER SCHEMAS ==========

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserResponse(UserBase):
    id: str
    created_at: str
    
    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    is_following: Optional[bool] = False
    follower_count: int = 0
    following_count: int = 0


# ========== AUTH SCHEMAS ==========

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ========== VIDEO SCHEMAS ==========

class VideoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    recipe: Optional[str] = Field(None, max_length=5000)
    visibility: str = Field("public", pattern="^(public|private)$")


class VideoCreate(VideoBase):
    pass


class VideoResponse(VideoBase):
    id: str
    blob_name: str
    blob_url: str
    user_id: str
    created_at: str
    
    class Config:
        from_attributes = True


class VideoStreamResponse(BaseModel):
    url: str


# ========== FOLLOW SCHEMAS ==========

class FollowResponse(BaseModel):
    message: str
    follow: Optional[dict] = None


class UnfollowResponse(BaseModel):
    message: str


# ========== MESSAGE SCHEMAS ==========

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str

