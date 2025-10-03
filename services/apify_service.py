import os
import json
import asyncio
import redis.asyncio as redis
from typing import List, Optional
from apify_client import ApifyClient
from models import VideoMetadata, Comment, Platform
import httpx
import re
from urllib.parse import urlparse, parse_qs
from services.storage_service import storage_service


class ApifyService:
    def __init__(self):
        self.apify_token = os.getenv("APIFY_TOKEN")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        if self.apify_token:
            self.client = ApifyClient(self.apify_token)

        self.redis_client = None

    async def get_redis_client(self):
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url)
        return self.redis_client

    async def cache_set(self, key: str, value: dict, expire_hours: int = 168):  # 7 dias
        try:
            redis_client = await self.get_redis_client()
            await redis_client.setex(key, expire_hours * 3600, json.dumps(value))
        except Exception:
            pass  # Cache silencioso

    async def cache_get(self, key: str) -> Optional[dict]:
        try:
            redis_client = await self.get_redis_client()
            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    def detect_platform(self, url: str) -> Platform:
        if "youtube.com" in url or "youtu.be" in url:
            return Platform.YOUTUBE
        elif "tiktok.com" in url:
            return Platform.TIKTOK
        elif "instagram.com" in url:
            return Platform.INSTAGRAM
        else:
            raise ValueError(f"Plataforma não suportada para URL: {url}")

    def extract_video_id_youtube(self, url: str) -> str:
        if "youtu.be/" in url:
            return url.split("youtu.be/")[-1].split("?")[0]
        elif "youtube.com/watch" in url:
            parsed = urlparse(url)
            return parse_qs(parsed.query)["v"][0]
        else:
            raise ValueError("URL do YouTube inválida")

    async def extract_youtube(self, url: str) -> VideoMetadata:
        cache_key = f"youtube:{url}"
        cached = await self.cache_get(cache_key)
        if cached:
            return VideoMetadata(**cached)

        if not self.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY não configurada")

        try:
            video_id = self.extract_video_id_youtube(url)

            async with httpx.AsyncClient() as client:
                # Buscar metadados do vídeo
                video_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "part": "snippet,statistics,contentDetails",
                        "id": video_id,
                        "key": self.youtube_api_key
                    }
                )
                video_data = video_response.json()

                if not video_data["items"]:
                    raise ValueError("Vídeo não encontrado")

                video_info = video_data["items"][0]
                snippet = video_info["snippet"]
                stats = video_info["statistics"]

                # Buscar comentários
                comments_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/commentThreads",
                    params={
                        "part": "snippet",
                        "videoId": video_id,
                        "maxResults": 50,
                        "order": "relevance",
                        "key": self.youtube_api_key
                    }
                )
                comments_data = comments_response.json()

                top_comments = []
                if "items" in comments_data:
                    for item in comments_data["items"]:
                        comment_snippet = item["snippet"]["topLevelComment"]["snippet"]
                        top_comments.append(Comment(
                            text=comment_snippet["textDisplay"],
                            author=comment_snippet["authorDisplayName"],
                            likes=comment_snippet.get("likeCount", 0)
                        ))

                # Extrair hashtags da descrição
                description = snippet.get("description", "")
                hashtags = re.findall(r"#\w+", description)

                metadata = VideoMetadata(
                    url=url,
                    platform=Platform.YOUTUBE,
                    title=snippet["title"],
                    description=description,
                    hashtags=hashtags,
                    views=int(stats.get("viewCount", 0)),
                    likes=int(stats.get("likeCount", 0)),
                    comments_count=int(stats.get("commentCount", 0)),
                    top_comments=top_comments,
                    thumbnail_url=snippet["thumbnails"]["high"]["url"],
                    duration=video_info["contentDetails"]["duration"],
                    author=snippet["channelTitle"],
                    author_url=f"https://www.youtube.com/channel/{snippet['channelId']}",
                    published_at=snippet["publishedAt"]
                )

                await self.cache_set(cache_key, metadata.dict())
                return metadata

        except Exception as e:
            raise ValueError(f"Erro ao extrair metadados do YouTube: {str(e)}")

    async def extract_tiktok(self, url: str) -> VideoMetadata:
        cache_key = f"tiktok:{url}"
        cached = await self.cache_get(cache_key)
        if cached:
            return VideoMetadata(**cached)

        if not self.apify_token:
            raise ValueError("APIFY_TOKEN não configurado")

        try:
            run_input = {
                "postUrls": [url],
                "maxItems": 1
            }

            run = self.client.actor("apify/tiktok-scraper").call(run_input=run_input)

            items = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)

            if not items:
                raise ValueError("Vídeo do TikTok não encontrado")

            data = items[0]

            # Extrair comentários se disponíveis
            top_comments = []
            if "comments" in data and data["comments"]:
                for comment in data["comments"][:50]:
                    top_comments.append(Comment(
                        text=comment.get("text", ""),
                        author=comment.get("author", ""),
                        likes=comment.get("diggCount", 0)
                    ))

            # Extrair hashtags
            text = data.get("text", "")
            hashtags = re.findall(r"#\w+", text)

            # Thumbnail temporária do Apify
            temp_thumbnail_url = data.get("imageURL", "")

            # Upload para Supabase Storage (permanente)
            permanent_thumbnail = await storage_service.upload_thumbnail(temp_thumbnail_url, url)
            final_thumbnail_url = permanent_thumbnail if permanent_thumbnail else temp_thumbnail_url

            metadata = VideoMetadata(
                url=url,
                platform=Platform.TIKTOK,
                title=text[:100] + "..." if len(text) > 100 else text,
                description=text,
                hashtags=hashtags,
                views=data.get("playCount", 0),
                likes=data.get("diggCount", 0),
                comments_count=data.get("commentCount", 0),
                top_comments=top_comments,
                thumbnail_url=final_thumbnail_url,
                duration=str(data.get("videoMeta", {}).get("duration", "")),
                author=data.get("authorMeta", {}).get("name", ""),
                author_url=f"https://www.tiktok.com/@{data.get('authorMeta', {}).get('name', '')}",
                published_at=data.get("createTime", "")
            )

            await self.cache_set(cache_key, metadata.dict())
            return metadata

        except Exception as e:
            raise ValueError(f"Erro ao extrair metadados do TikTok: {str(e)}")

    async def extract_instagram_reel(self, url: str) -> VideoMetadata:
        cache_key = f"instagram:{url}"
        cached = await self.cache_get(cache_key)
        if cached:
            return VideoMetadata(**cached)

        if not self.apify_token:
            raise ValueError("APIFY_TOKEN não configurado")

        try:
            run_input = {
                "directUrls": [url],
                "resultsType": "posts",
                "resultsLimit": 1,
                "searchType": "hashtag",
                "searchLimit": 1
            }

            run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)

            items = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)

            if not items:
                raise ValueError("Reel do Instagram não encontrado")

            data = items[0]

            # Extrair comentários se disponíveis
            top_comments = []
            if "latestComments" in data and data["latestComments"]:
                for comment in data["latestComments"][:50]:
                    top_comments.append(Comment(
                        text=comment.get("text", ""),
                        author=comment.get("ownerUsername", ""),
                        likes=comment.get("likesCount", 0)
                    ))

            # Extrair hashtags da caption
            caption = data.get("caption", "")
            hashtags = re.findall(r"#\w+", caption)

            # Thumbnail temporária do Apify
            temp_thumbnail_url = data.get("displayUrl", "")

            # Upload para Supabase Storage (permanente)
            permanent_thumbnail = await storage_service.upload_thumbnail(temp_thumbnail_url, url)
            final_thumbnail_url = permanent_thumbnail if permanent_thumbnail else temp_thumbnail_url

            metadata = VideoMetadata(
                url=url,
                platform=Platform.INSTAGRAM,
                title=caption[:100] + "..." if len(caption) > 100 else caption,
                description=caption,
                hashtags=hashtags,
                views=data.get("videoViewCount", 0),
                likes=data.get("likesCount", 0),
                comments_count=data.get("commentsCount", 0),
                top_comments=top_comments,
                thumbnail_url=final_thumbnail_url,
                duration=str(data.get("videoDuration", "")),
                author=data.get("ownerUsername", ""),
                author_url=f"https://www.instagram.com/{data.get('ownerUsername', '')}",
                published_at=data.get("timestamp", "")
            )

            await self.cache_set(cache_key, metadata.dict())
            return metadata

        except Exception as e:
            raise ValueError(f"Erro ao extrair metadados do Instagram: {str(e)}")

    async def extract_metadata(self, url: str) -> VideoMetadata:
        platform = self.detect_platform(url)

        if platform == Platform.YOUTUBE:
            return await self.extract_youtube(url)
        elif platform == Platform.TIKTOK:
            return await self.extract_tiktok(url)
        elif platform == Platform.INSTAGRAM:
            return await self.extract_instagram_reel(url)
        else:
            raise ValueError(f"Plataforma não suportada: {platform}")

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()