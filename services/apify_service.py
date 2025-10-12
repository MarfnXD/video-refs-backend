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
            # Fallback: retorna metadados básicos sem Apify
            return await self._instagram_fallback(url)

        try:
            run_input = {
                "directUrls": [url],
                "resultsType": "posts",
                "resultsLimit": 1,
                "searchType": "hashtag",
                "searchLimit": 1,
                "addParentData": False  # Reduz dados para evitar timeouts
            }

            # Timeout reduzido para detectar falhas mais rápido
            run = self.client.actor("apify/instagram-scraper").call(
                run_input=run_input,
                timeout_secs=30  # 30 segundos max
            )

            items = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)
                break  # Apenas 1 item

            if not items:
                print("⚠️ Instagram scraper retornou vazio - usando fallback")
                return await self._instagram_fallback(url)

            data = items[0]

            # Validação de dados essenciais
            if not data.get("caption") and not data.get("ownerUsername"):
                print("⚠️ Instagram scraper retornou dados incompletos - usando fallback")
                return await self._instagram_fallback(url)

            # Extrair comentários se disponíveis (com proteção)
            top_comments = []
            try:
                if "latestComments" in data and data["latestComments"]:
                    for comment in data["latestComments"][:50]:
                        if comment.get("text"):  # Valida que tem texto
                            top_comments.append(Comment(
                                text=comment.get("text", ""),
                                author=comment.get("ownerUsername", ""),
                                likes=comment.get("likesCount", 0)
                            ))
            except Exception:
                pass  # Ignora erros em comentários

            # Extrair hashtags da caption
            caption = data.get("caption", "Instagram Reel")
            hashtags = re.findall(r"#\w+", caption)

            # Thumbnail temporária do Apify
            temp_thumbnail_url = data.get("displayUrl", "")

            # Upload para Supabase Storage (permanente) com proteção
            final_thumbnail_url = temp_thumbnail_url
            try:
                if temp_thumbnail_url:
                    permanent_thumbnail = await storage_service.upload_thumbnail(temp_thumbnail_url, url)
                    if permanent_thumbnail:
                        final_thumbnail_url = permanent_thumbnail
            except Exception:
                pass  # Usa thumbnail temporária se upload falhar

            metadata = VideoMetadata(
                url=url,
                platform=Platform.INSTAGRAM,
                title=caption[:100] + "..." if len(caption) > 100 else caption if caption else "Instagram Reel",
                description=caption,
                hashtags=hashtags,
                views=data.get("videoViewCount", 0),
                likes=data.get("likesCount", 0),
                comments_count=data.get("commentsCount", 0),
                top_comments=top_comments,
                thumbnail_url=final_thumbnail_url,
                duration=str(data.get("videoDuration", "")) if data.get("videoDuration") else "",
                author=data.get("ownerUsername", "Unknown"),
                author_url=f"https://www.instagram.com/{data.get('ownerUsername', '')}" if data.get('ownerUsername') else "",
                published_at=data.get("timestamp", "")
            )

            await self.cache_set(cache_key, metadata.dict())
            return metadata

        except Exception as e:
            print(f"❌ Erro no Instagram scraper: {str(e)} - usando fallback")
            return await self._instagram_fallback(url)

    async def _instagram_fallback(self, url: str) -> VideoMetadata:
        """Fallback quando Apify falha - retorna metadados básicos"""
        # Extrai ID do reel/post da URL
        reel_match = re.search(r'/reel/([A-Za-z0-9_-]+)', url)
        post_match = re.search(r'/p/([A-Za-z0-9_-]+)', url)

        post_id = None
        if reel_match:
            post_id = reel_match.group(1)
            title = f"Instagram Reel {post_id[:8]}"
        elif post_match:
            post_id = post_match.group(1)
            title = f"Instagram Post {post_id[:8]}"
        else:
            title = "Instagram Video"

        return VideoMetadata(
            url=url,
            platform=Platform.INSTAGRAM,
            title=title,
            description="",
            hashtags=[],
            views=0,
            likes=0,
            comments_count=0,
            top_comments=[],
            thumbnail_url="",
            duration="",
            author="",
            author_url="",
            published_at=""
        )

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

    async def extract_video_download_url_tiktok(self, url: str, quality: str = "480p") -> dict:
        """
        Extrai URL de download direto do vídeo do TikTok.

        Retorna:
        - download_url: URL direta do vídeo
        - file_size_mb: Tamanho estimado
        - quality: Qualidade real do vídeo
        - expires_in_hours: Validade da URL
        """
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

            # TikTok retorna videoUrl no campo "video"
            video_url = None
            file_size_mb = None

            # Estrutura do TikTok Apify response:
            # - data["video"]["downloadAddr"] = URL de download direto
            # - data["videoMeta"]["width"], data["videoMeta"]["height"] = dimensões
            # - data["videoMeta"]["duration"] = duração em segundos

            if "video" in data:
                video_data = data["video"]
                # URL de download direto (HD se disponível)
                video_url = video_data.get("downloadAddr") or video_data.get("playAddr")

                # Tamanho estimado (TikTok não sempre retorna, estimamos)
                if "videoMeta" in data:
                    duration = data["videoMeta"].get("duration", 0)
                    # Estimativa: ~1MB por 10 segundos em 480p
                    file_size_mb = round((duration / 10) * 1.0, 2)

            if not video_url:
                raise ValueError("URL de vídeo não encontrada no response do TikTok")

            return {
                "download_url": video_url,
                "file_size_mb": file_size_mb,
                "quality": "original",  # TikTok geralmente retorna qualidade original
                "expires_in_hours": 6,  # URLs do TikTok expiram em ~6 horas
            }

        except Exception as e:
            raise ValueError(f"Erro ao extrair URL de download do TikTok: {str(e)}")

    async def extract_video_download_url_instagram(self, url: str, quality: str = "480p") -> dict:
        """
        Extrai URL de download direto do vídeo do Instagram.

        Retorna:
        - download_url: URL direta do vídeo
        - file_size_mb: Tamanho estimado
        - quality: Qualidade real do vídeo
        - expires_in_hours: Validade da URL
        """
        # Tenta Apify primeiro (evita rate-limit do Instagram)
        try:
            run_input = {
                "directUrls": [url],
                "resultsType": "posts",
                "resultsLimit": 1,
                "searchType": "hashtag",
                "searchLimit": 1,
                "addParentData": False
            }

            run = self.client.actor("apify/instagram-scraper").call(
                run_input=run_input,
                timeout_secs=30
            )

            items = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)
                break

            if not items:
                print("⚠️ Apify Instagram vazio - tentando yt-dlp")
                return await self._extract_instagram_ytdlp(url, quality)

            data = items[0]

            # Instagram retorna videoUrl no campo "videoUrl"
            video_url = data.get("videoUrl")

            if not video_url:
                print("⚠️ Apify não retornou videoUrl - tentando yt-dlp")
                return await self._extract_instagram_ytdlp(url, quality)

            # Tamanho estimado
            file_size_mb = None
            if "videoDuration" in data:
                duration = data["videoDuration"]
                # Estimativa: ~1.5MB por 10 segundos em 480p
                file_size_mb = round((duration / 10) * 1.5, 2)

            print("✅ URL de vídeo Instagram extraída via Apify")
            return {
                "download_url": video_url,
                "file_size_mb": file_size_mb,
                "quality": "original",  # Instagram retorna qualidade original
                "expires_in_hours": 2,  # URLs do Instagram expiram em ~2 horas
            }

        except Exception as e:
            print(f"❌ Apify falhou: {str(e)} - tentando yt-dlp")
            return await self._extract_instagram_ytdlp(url, quality)

    async def _extract_instagram_ytdlp(self, url: str, quality: str = "480p") -> dict:
        """Fallback usando yt-dlp para Instagram com formato compatível Android"""
        try:
            import subprocess
            import json
            import tempfile

            print(f"🔧 Tentando yt-dlp para Instagram: {url}")

            # Definir qualidade baseada no parâmetro com MÚLTIPLOS FALLBACKS
            # Tenta H.264 primeiro, mas aceita qualquer formato se não houver
            # Fallback chain: H.264+MP4 → Qualquer MP4 → Qualquer formato com altura limitada → Melhor disponível
            quality_map = {
                "low": "worst[ext=mp4][vcodec^=avc1]/worst[ext=mp4]/worst",
                "medium": "best[height<=480][ext=mp4][vcodec^=avc1]/best[height<=480][ext=mp4]/best[height<=480]/best",
                "high": "best[height<=720][ext=mp4][vcodec^=avc1]/best[height<=720][ext=mp4]/best[height<=720]/best"
            }
            format_selector = quality_map.get(quality, "best[height<=480][ext=mp4][vcodec^=avc1]/best[height<=480][ext=mp4]/best[height<=480]/best")

            # Montar comando base
            cmd = [
                "yt-dlp",
                "-j",  # JSON output
                "--no-warnings",
                "--no-check-certificates",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "-f", format_selector,  # Seleciona formato compatível
                "--prefer-free-formats",  # Prefere formatos livres (geralmente mais compatíveis)
            ]

            # Adicionar cookies se configurados
            instagram_cookies = os.getenv("INSTAGRAM_COOKIES")
            cookies_file = None

            if instagram_cookies:
                # Criar arquivo temporário com cookies
                cookies_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                cookies_file.write(instagram_cookies)
                cookies_file.close()
                cmd.extend(["--cookies", cookies_file.name])
                print("🍪 Usando cookies do Instagram configurados")

            cmd.append(url)

            # yt-dlp com formato específico compatível com Android
            # Prioriza H.264 (avc1) em MP4 para máxima compatibilidade
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Limpar arquivo de cookies temporário
            if cookies_file:
                try:
                    import os as os_module
                    os_module.unlink(cookies_file.name)
                except:
                    pass

            if result.returncode != 0:
                print(f"⚠️ yt-dlp stderr: {result.stderr}")
                raise ValueError(f"yt-dlp falhou: {result.stderr}")

            # Limpar output
            stdout_lines = result.stdout.strip().split('\n')
            json_line = None
            for line in stdout_lines:
                if line.startswith('{'):
                    json_line = line
                    break

            if not json_line:
                raise ValueError("yt-dlp não retornou JSON válido")

            data = json.loads(json_line)

            # Pegar URL do formato selecionado
            video_url = data.get("url")
            file_size_mb = None

            if "filesize" in data and data["filesize"]:
                file_size_mb = round(data["filesize"] / (1024 * 1024), 2)
            elif "filesize_approx" in data and data["filesize_approx"]:
                file_size_mb = round(data["filesize_approx"] / (1024 * 1024), 2)

            if not video_url:
                raise ValueError("URL de vídeo não encontrada no output do yt-dlp")

            print(f"✅ yt-dlp extraiu URL com sucesso (formato: {data.get('format_id')})")
            return {
                "download_url": video_url,
                "file_size_mb": file_size_mb,
                "quality": quality,
                "expires_in_hours": 2,
            }

        except Exception as e:
            print(f"❌ yt-dlp falhou completamente: {str(e)}")
            raise ValueError(f"Erro ao extrair URL de download do Instagram (yt-dlp): {str(e)}")

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()