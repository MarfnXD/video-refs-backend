from typing import List, Optional
from pydantic import BaseModel
from enum import Enum


class Platform(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


class Comment(BaseModel):
    text: str
    author: str
    likes: int


class VideoMetadata(BaseModel):
    url: str
    platform: Platform
    title: str
    description: Optional[str] = None
    hashtags: List[str] = []
    views: Optional[int] = None
    likes: Optional[int] = None
    comments_count: Optional[int] = None
    top_comments: List[Comment] = []
    thumbnail_url: Optional[str] = None
    duration: Optional[str] = None
    author: Optional[str] = None
    author_url: Optional[str] = None
    published_at: Optional[str] = None