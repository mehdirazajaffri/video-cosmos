# app/routers/users.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import (
    UserResponse,
    UserProfile,
    VideoResponse,
    FollowResponse,
    UnfollowResponse
)
from app.db import (
    get_user_by_id,
    get_videos_by_user_id,
    get_videos_by_user_ids,
    follow_user,
    unfollow_user,
    get_following_ids,
    get_follower_ids,
    get_follow
)
from app.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user profile information"""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found"
        )
    
    # Check if current user is following this user
    is_following = get_follow(current_user["id"], user_id) is not None
    
    # Get follower and following counts
    follower_count = len(get_follower_ids(user_id))
    following_count = len(get_following_ids(user_id))
    
    return UserProfile(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        created_at=user.get("created_at", ""),
        is_following=is_following,
        follower_count=follower_count,
        following_count=following_count
    )


@router.get("/{user_id}/videos", response_model=List[VideoResponse])
async def get_user_videos(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all videos by a specific user (requires authentication)"""
    # Check if user exists
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found"
        )
    
    videos = get_videos_by_user_id(user_id)
    
    # Filter out private videos if not the owner
    if user_id != current_user["id"]:
        videos = [v for v in videos if v["visibility"] == "public"]
    
    return [VideoResponse(**video) for video in videos]


@router.post("/{user_id}/follow", response_model=FollowResponse)
async def follow_user_endpoint(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Follow a user (requires authentication)"""
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    # Check if user exists
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found"
        )
    
    try:
        follow = follow_user(current_user["id"], user_id)
        return FollowResponse(
            message=f"You are now following {user['username']}",
            follow=follow
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{user_id}/follow", response_model=UnfollowResponse)
async def unfollow_user_endpoint(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unfollow a user (requires authentication)"""
    success = unfollow_user(current_user["id"], user_id)
    if success:
        return UnfollowResponse(message="Successfully unfollowed user")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not following this user"
        )


@router.get("/{user_id}/followers", response_model=List[UserResponse])
async def get_followers(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get list of users following a specific user"""
    follower_ids = get_follower_ids(user_id)
    followers = [get_user_by_id(fid) for fid in follower_ids]
    followers = [f for f in followers if f]  # Remove None values
    
    return [
        UserResponse(
            id=f["id"],
            username=f["username"],
            email=f["email"],
            created_at=f.get("created_at", "")
        )
        for f in followers
    ]


@router.get("/{user_id}/following", response_model=List[UserResponse])
async def get_following(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get list of users that a specific user is following"""
    following_ids = get_following_ids(user_id)
    following = [get_user_by_id(fid) for fid in following_ids]
    following = [f for f in following if f]  # Remove None values
    
    return [
        UserResponse(
            id=f["id"],
            username=f["username"],
            email=f["email"],
            created_at=f.get("created_at", "")
        )
        for f in following
    ]



