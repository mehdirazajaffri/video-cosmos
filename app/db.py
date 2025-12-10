# app/db.py
import os
import uuid
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from typing import Optional, List

# Load environment variables from .env file
load_dotenv()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB = os.getenv("COSMOS_DATABASE", "videosdb")

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    raise ValueError(
        "Cosmos DB credentials not configured. "
        "Please set COSMOS_ENDPOINT and COSMOS_KEY environment variables."
    )

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.create_database_if_not_exists(id=COSMOS_DB)

# Containers
# Videos container - partitioned by visibility
videos_container = database.create_container_if_not_exists(
    id="videos",
    partition_key=PartitionKey(path="/visibility")
)

# Users container - partitioned by id
users_container = database.create_container_if_not_exists(
    id="users",
    partition_key=PartitionKey(path="/id")
)

# Follows container - partitioned by follower_id
follows_container = database.create_container_if_not_exists(
    id="follows",
    partition_key=PartitionKey(path="/follower_id")
)

# ========== USER FUNCTIONS ==========

def create_user(username: str, email: str, password_hash: str) -> dict:
    """Create a new user"""
    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    users_container.create_item(body=user)
    # Remove password hash from returned user
    user.pop("password_hash", None)
    return user


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username"""
    query = "SELECT * FROM c WHERE c.username = @username"
    items = list(users_container.query_items(
        query=query,
        parameters=[{"name": "@username", "value": username}],
        enable_cross_partition_query=True
    ))
    return items[0] if items else None


def get_user_by_username_with_password(username: str) -> Optional[dict]:
    """Get user by username including password hash (for authentication)"""
    query = "SELECT * FROM c WHERE c.username = @username"
    items = list(users_container.query_items(
        query=query,
        parameters=[{"name": "@username", "value": username}],
        enable_cross_partition_query=True
    ))
    return items[0] if items else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID - tries read_item first, falls back to query if needed"""
    if not user_id:
        return None
    
    try:
        # First try: Use read_item (faster, requires exact partition key match)
        user = users_container.read_item(item=user_id, partition_key=user_id)
        # Remove password hash before returning
        if "password_hash" in user:
            user.pop("password_hash", None)
        return user
    except exceptions.CosmosResourceNotFoundError:
        # Fallback: Use query in case partition key doesn't match exactly
        try:
            query = "SELECT * FROM c WHERE c.id = @id"
            items = list(users_container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": user_id}],
                enable_cross_partition_query=True
            ))
            if items:
                user = items[0]
                if "password_hash" in user:
                    user.pop("password_hash", None)
                return user
        except Exception:
            pass
        return None
    except Exception as e:
        # Log error in production - for now just return None
        # In production, use proper logging
        return None


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    query = "SELECT * FROM c WHERE c.email = @email"
    items = list(users_container.query_items(
        query=query,
        parameters=[{"name": "@email", "value": email}],
        enable_cross_partition_query=True
    ))
    if items:
        items[0].pop("password_hash", None)
    return items[0] if items else None


# ========== VIDEO FUNCTIONS ==========

def create_video_item(
    title: str,
    blob_name: str,
    blob_url: str,
    user_id: str,
    visibility: str = "public",
    recipe: Optional[str] = None,
    extra=None
) -> dict:
    """Create a new video item"""
    item = {
        "id": str(uuid.uuid4()),
        "title": title,
        "blob_name": blob_name,
        "blob_url": blob_url,
        "user_id": user_id,
        "visibility": visibility,
        "recipe": recipe or "",
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    if extra:
        item.update(extra)
    videos_container.create_item(body=item)
    return item


def list_public_videos(limit: int = 100) -> List[dict]:
    """List all public videos"""
    query = "SELECT * FROM c WHERE c.visibility = 'public' ORDER BY c.created_at DESC"
    items = list(videos_container.query_items(
        query=query,
        enable_cross_partition_query=True,
        max_item_count=limit
    ))
    return items


def get_video_by_id(video_id: str) -> Optional[dict]:
    """Get video by ID"""
    query = "SELECT * FROM c WHERE c.id = @id"
    items = list(videos_container.query_items(
        query=query,
        parameters=[{"name": "@id", "value": video_id}],
        enable_cross_partition_query=True
    ))
    return items[0] if items else None


def get_videos_by_user_id(user_id: str, limit: int = 100) -> List[dict]:
    """Get all videos by a specific user"""
    query = "SELECT * FROM c WHERE c.user_id = @user_id ORDER BY c.created_at DESC"
    items = list(videos_container.query_items(
        query=query,
        parameters=[{"name": "@user_id", "value": user_id}],
        enable_cross_partition_query=True,
        max_item_count=limit
    ))
    return items


def get_videos_by_user_ids(user_ids: List[str], limit: int = 100) -> List[dict]:
    """Get videos from multiple users (for feed)"""
    if not user_ids:
        return []
    
    # Build query with IN clause
    user_ids_str = ", ".join([f"'{uid}'" for uid in user_ids])
    query = f"SELECT * FROM c WHERE c.user_id IN ({user_ids_str}) AND c.visibility = 'public' ORDER BY c.created_at DESC"
    items = list(videos_container.query_items(
        query=query,
        enable_cross_partition_query=True,
        max_item_count=limit
    ))
    return items


# ========== FOLLOW FUNCTIONS ==========

def follow_user(follower_id: str, following_id: str) -> dict:
    """Create a follow relationship"""
    if follower_id == following_id:
        raise ValueError("Cannot follow yourself")
    
    # Check if already following
    existing = get_follow(follower_id, following_id)
    if existing:
        return existing
    
    follow = {
        "id": str(uuid.uuid4()),
        "follower_id": follower_id,
        "following_id": following_id,
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    follows_container.create_item(body=follow)
    return follow


def unfollow_user(follower_id: str, following_id: str) -> bool:
    """Remove a follow relationship"""
    follow = get_follow(follower_id, following_id)
    if not follow:
        return False
    
    try:
        follows_container.delete_item(item=follow["id"], partition_key=follower_id)
        return True
    except Exception:
        return False


def get_follow(follower_id: str, following_id: str) -> Optional[dict]:
    """Check if a follow relationship exists"""
    query = "SELECT * FROM c WHERE c.follower_id = @follower_id AND c.following_id = @following_id"
    items = list(follows_container.query_items(
        query=query,
        parameters=[
            {"name": "@follower_id", "value": follower_id},
            {"name": "@following_id", "value": following_id}
        ],
        enable_cross_partition_query=True
    ))
    return items[0] if items else None


def get_following_ids(user_id: str) -> List[str]:
    """Get list of user IDs that a user is following"""
    query = "SELECT c.following_id FROM c WHERE c.follower_id = @follower_id"
    items = list(follows_container.query_items(
        query=query,
        parameters=[{"name": "@follower_id", "value": user_id}],
        enable_cross_partition_query=True
    ))
    return [item["following_id"] for item in items]


def get_follower_ids(user_id: str) -> List[str]:
    """Get list of user IDs that are following a user"""
    query = "SELECT c.follower_id FROM c WHERE c.following_id = @following_id"
    items = list(follows_container.query_items(
        query=query,
        parameters=[{"name": "@following_id", "value": user_id}],
        enable_cross_partition_query=True
    ))
    return [item["follower_id"] for item in items]