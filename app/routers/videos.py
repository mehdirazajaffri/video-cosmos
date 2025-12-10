# app/routers/videos.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form

from app.schemas import VideoCreate, VideoResponse, VideoStreamResponse
from app.db import (
    create_video_item,
    list_public_videos,
    get_video_by_id,
    get_videos_by_user_id
)
from app.storage import upload_blob_from_stream, generate_blob_sas_url
from app.auth import get_current_user
import time
import uuid

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    title: str = Form(..., min_length=1, max_length=200),
    file: UploadFile = File(...),
    recipe: Optional[str] = Form(None, max_length=5000),
    visibility: str = Form("public"),
    current_user: dict = Depends(get_current_user)
):
    """Upload a video (requires authentication)"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file required"
        )
    
    if visibility not in ["public", "private"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="visibility must be 'public' or 'private'"
        )
    
    # Generate unique blob name
    ext = file.filename.split(".")[-1] if "." in file.filename else ""
    blob_name = (
        f"{int(time.time())}-{uuid.uuid4()}.{ext}"
        if ext
        else f"{int(time.time())}-{uuid.uuid4()}"
    )
    
    # Read file contents
    contents = await file.read()
    length = len(contents)
    
    try:
        blob_url = upload_blob_from_stream(
            blob_name, contents, length, content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"upload failed: {str(e)}"
        )
    
    # Create video item with user_id and recipe
    item = create_video_item(
        title=title,
        blob_name=blob_name,
        blob_url=blob_url,
        user_id=current_user["id"],
        visibility=visibility,
        recipe=recipe
    )
    
    return VideoResponse(**item)


@router.get("", response_model=list[VideoResponse])
async def list_videos(current_user: dict = Depends(get_current_user)):
    """List all public videos (requires authentication)"""
    items = list_public_videos()
    return [VideoResponse(**item) for item in items]


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get video by ID (requires authentication)"""
    item = get_video_by_id(video_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="video not found"
        )
    
    # Check if user can view this video
    if item["visibility"] == "private" and item["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this video"
        )
    
    return VideoResponse(**item)


@router.get("/{video_id}/stream", response_model=VideoStreamResponse)
async def stream_video(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get streaming URL for a video (requires authentication)"""
    item = get_video_by_id(video_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="video not found"
        )
    
    # Check if user can view this video
    if item["visibility"] == "private" and item["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this video"
        )
    
    sas_url = generate_blob_sas_url(item["blob_name"])
    return VideoStreamResponse(url=sas_url)

