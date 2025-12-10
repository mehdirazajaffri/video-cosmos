# app/routers/feed.py
from typing import List
from fastapi import APIRouter, Depends

from app.schemas import VideoResponse
from app.db import get_following_ids, get_videos_by_user_ids
from app.auth import get_current_user

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=List[VideoResponse])
async def get_feed(current_user: dict = Depends(get_current_user)):
    """Get feed of videos from users you follow (requires authentication)"""
    # Get list of user IDs you're following
    following_ids = get_following_ids(current_user["id"])
    
    if not following_ids:
        return []
    
    # Get videos from followed users
    videos = get_videos_by_user_ids(following_ids)
    return [VideoResponse(**video) for video in videos]

