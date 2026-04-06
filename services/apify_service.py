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
        # Suporte a múltiplas chaves Apify (2 formatos):
        # Formato 1: APIFY_TOKEN="token1,token2,token3"
        # Formato 2: APIFY_TOKEN, APIFY_TOKEN_2, APIFY_TOKEN_3, etc
        self.apify_tokens = []

        # Tenta formato 1 (comma-separated)
        apify_tokens_str = os.getenv("APIFY_TOKEN", "")
        if ',' in apify_tokens_str:
            self.apify_tokens = [t.strip() for t in apify_tokens_str.split(',') if t.strip()]
        else:
            # Formato 2 (variáveis separadas)
            if apify_tokens_str:
                self.apify_tokens.append(apify_tokens_str.strip())

            # Procura APIFY_TOKEN_2, APIFY_TOKEN_3, etc
            i = 2
            while True:
                token = os.getenv(f"APIFY_TOKEN_{i}")
                if not token:
                    break
                self.apify_tokens.append(token.strip())
                i += 1

        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Cria clientes para cada token
        self.clients = [ApifyClient(token) for token in self.apify_tokens] if self.apify_tokens else []
        self._current_client_index = 0

        # Mantém compatibilidade com código antigo
        self.apify_token = self.apify_tokens[0] if self.apify_tokens else None
        self.client = self.clients[0] if self.clients else None

        self.redis_client = None

        # Armazena última resposta bruta do Apify para debug
        self.last_raw_response = None

    def _get_next_client(self) -> ApifyClient:
        """Rotaciona entre os clientes Apify (round-robin)"""
        if not self.clients:
            raise ValueError("Nenhum APIFY_TOKEN configurado")

        client = self.clients[self._current_client_index]
        # Print ANTES de incrementar para mostrar o índice correto
        print(f"🔄 Usando Apify token #{self._current_client_index + 1}/{len(self.clients)}")

        self._current_client_index = (self._current_client_index + 1) % len(self.clients)
        return client

    async def _try_all_clients(self, operation_func, operation_name: str = "operação"):
        """
        Tenta executar uma operação com todos os clientes Apify até conseguir.
        Se um token atingir o limite mensal, tenta automaticamente o próximo.

        Args:
            operation_func: Função async que recebe ApifyClient e retorna o resultado
            operation_name: Nome da operação para logs

        Returns:
            Resultado da operação bem-sucedida

        Raises:
            ValueError: Se TODOS os tokens falharem
        """
        if not self.clients:
            raise ValueError("Nenhum APIFY_TOKEN configurado")

        last_error = None
        attempts = len(self.clients)  # Tenta todos os tokens disponíveis

        for attempt in range(attempts):
            try:
                client = self._get_next_client()
                print(f"🔄 Tentativa {attempt + 1}/{attempts} para {operation_name}")

                result = await operation_func(client)
                print(f"✅ {operation_name} bem-sucedida com token #{self._current_client_index}/{len(self.clients)}")
                return result

            except Exception as e:
                error_msg = str(e).lower()

                # Detecta erro de limite mensal
                if "monthly usage" in error_msg or "hard limit" in error_msg or "limit exceeded" in error_msg:
                    print(f"⚠️ Token #{self._current_client_index}/{len(self.clients)} atingiu limite mensal - tentando próximo token...")
                    last_error = e
                    continue

                # Outros erros (não relacionados a limite) - falha imediatamente
                print(f"❌ Erro inesperado em {operation_name}: {str(e)}")
                raise

        # Se chegou aqui, TODOS os tokens falharam
        print(f"❌ TODOS os {attempts} tokens Apify atingiram limite mensal!")
        raise ValueError(f"Todos os tokens Apify esgotados. Último erro: {str(last_error)}")

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
        elif "x.com" in url or "twitter.com" in url:
            return Platform.X
        elif "threads.net" in url or "threads.com" in url:
            return Platform.THREADS
        else:
            raise ValueError(f"Plataforma não suportada para URL: {url}")

    def extract_video_id_youtube(self, url: str) -> str:
        if "youtu.be/" in url:
            return url.split("youtu.be/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in url:
            return url.split("youtube.com/shorts/")[-1].split("?")[0].split("/")[0]
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
                    # Extrair comentários da resposta
                    comments_list = []
                    for item in comments_data["items"]:
                        comment_snippet = item["snippet"]["topLevelComment"]["snippet"]
                        comments_list.append({
                            "text": comment_snippet["textDisplay"],
                            "author": comment_snippet["authorDisplayName"],
                            "likes": comment_snippet.get("likeCount", 0)
                        })

                    # Ordenar por likes (garantir que os mais relevantes vêm primeiro)
                    sorted_comments = sorted(
                        comments_list,
                        key=lambda x: x.get("likes", 0),
                        reverse=True
                    )

                    # Converter para objetos Comment
                    for comment in sorted_comments:
                        top_comments.append(Comment(
                            text=comment["text"],
                            author=comment["author"],
                            likes=comment["likes"]
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

            # Função para executar scraping TikTok com um cliente específico
            async def run_tiktok_scraper(client: ApifyClient):
                run = client.actor("apify/tiktok-scraper").call(run_input=run_input)
                items = []
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)
                if not items:
                    raise ValueError("Vídeo do TikTok não encontrado")
                return items[0]

            # Tenta com todos os tokens disponíveis até conseguir
            data = await self._try_all_clients(run_tiktok_scraper, "extract_tiktok")

            # Extrair comentários se disponíveis (ordenados por likes)
            top_comments = []
            if "comments" in data and data["comments"]:
                # Converter para lista e ordenar por likes (comentários mais relevantes primeiro)
                comments_list = [
                    c for c in data["comments"][:200]
                    if c.get("text")  # Só comentários com texto
                ]

                # Ordenar por diggCount (likes no TikTok)
                sorted_comments = sorted(
                    comments_list,
                    key=lambda x: x.get("diggCount", 0),
                    reverse=True
                )

                # Pegar top 50 comentários com mais likes
                for comment in sorted_comments[:50]:
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
                "addParentData": False,  # Reduz dados para evitar timeouts
                # NOTA: latestComments retorna apenas ~6 comentários (preview)
                # Para extrair TODOS os comentários, use extract_all_comments()
                "extendOutputFunction": "",
                "extendScraperFunction": ""
            }

            # Função para executar scraping Instagram com um cliente específico
            async def run_instagram_scraper(client: ApifyClient):
                run = client.actor("apify/instagram-scraper").call(
                    run_input=run_input,
                    timeout_secs=120  # 2 minutos max
                )
                items = []
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)
                    break  # Apenas 1 item
                if not items:
                    raise ValueError("Instagram scraper retornou vazio")
                return items[0]

            # Tenta com todos os tokens disponíveis até conseguir
            data = await self._try_all_clients(run_instagram_scraper, "extract_instagram_reel")

            # Salva resposta bruta para debug
            self.last_raw_response = data

            # Validação de dados essenciais
            # NOTA: Aceita dados parciais se tiver error (página restrita mas com thumbnail)
            if not data.get("caption") and not data.get("ownerUsername") and not data.get("error"):
                print("⚠️ Instagram scraper retornou dados incompletos - usando fallback")
                self.last_raw_response = {"fallback": True, "reason": "dados_incompletos", "original": data}
                return await self._instagram_fallback(url)

            # Extrair comentários se disponíveis (ordenados por likes)
            top_comments = []
            try:
                if "latestComments" in data and data["latestComments"]:
                    # Converter para lista e ordenar por likes (comentários mais relevantes primeiro)
                    comments_list = [
                        c for c in data["latestComments"][:200]
                        if c.get("text")  # Só comentários com texto
                    ]

                    # Ordenar por likesCount (descendente)
                    sorted_comments = sorted(
                        comments_list,
                        key=lambda x: x.get("likesCount", 0),
                        reverse=True
                    )

                    # Pegar top 50 comentários com mais likes
                    for comment in sorted_comments[:50]:
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

            # Thumbnail original do Instagram (CDN)
            thumbnail_url = data.get("displayUrl") or data.get("image") or ""

            # Detectar carousel (sidecar) e extrair todos os media items
            carousel_items = []
            sidecar = data.get("childPosts") or data.get("sidecarMediaResources") or data.get("images") or []
            if sidecar and isinstance(sidecar, list) and len(sidecar) > 1:
                print(f"🎠 Carousel detectado: {len(sidecar)} items")
                for i, item in enumerate(sidecar):
                    media_item = {
                        "index": i,
                        "type": "video" if item.get("videoUrl") or item.get("type") == "Video" else "image",
                        "url": item.get("videoUrl") or item.get("url") or item.get("displayUrl") or item.get("src") or "",
                        "thumbnail": item.get("displayUrl") or item.get("url") or item.get("src") or "",
                    }
                    carousel_items.append(media_item)
                # Usar thumbnail do primeiro item se disponivel
                if not thumbnail_url and carousel_items:
                    thumbnail_url = carousel_items[0].get("thumbnail", "")

            # Log se veio de resposta restrita
            if data.get("error"):
                print(f"⚠️ Apify retornou erro parcial: {data.get('error')} - {data.get('errorDescription', '')}")

            # Determinar tipo de post
            post_type = data.get("type", "").lower()
            if carousel_items:
                post_type = "carousel"
            elif data.get("videoUrl") or data.get("videoDuration"):
                post_type = "video"
            else:
                post_type = "image"

            title_prefix = {"carousel": "Instagram Carousel", "video": "Instagram Reel", "image": "Instagram Post"}.get(post_type, "Instagram Post")
            title = caption[:100] + "..." if len(caption) > 100 else caption if caption else title_prefix

            metadata = VideoMetadata(
                url=url,
                platform=Platform.INSTAGRAM,
                title=title,
                description=caption,
                hashtags=hashtags,
                views=data.get("videoViewCount", 0),
                likes=data.get("likesCount", 0),
                comments_count=data.get("commentsCount", 0),
                top_comments=top_comments,
                thumbnail_url=thumbnail_url,
                duration=str(data.get("videoDuration", "")) if data.get("videoDuration") else "",
                author=data.get("ownerUsername", "Unknown"),
                author_url=f"https://www.instagram.com/{data.get('ownerUsername', '')}" if data.get('ownerUsername') else "",
                published_at=data.get("timestamp", "")
            )

            # Salvar carousel items no metadata extra (acessivel via metadata JSON no Supabase)
            if carousel_items:
                metadata_dict = metadata.dict()
                metadata_dict["carousel_items"] = carousel_items
                metadata_dict["post_type"] = post_type
                metadata_dict["carousel_count"] = len(carousel_items)
                await self.cache_set(cache_key, metadata_dict)
                return metadata

            await self.cache_set(cache_key, metadata.dict())
            return metadata

        except Exception as e:
            print(f"❌ Erro no Instagram scraper: {str(e)} - usando fallback")
            self.last_raw_response = {"fallback": True, "reason": "exception", "error": str(e)}
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
        elif platform == Platform.X:
            return await self.extract_x_tweet(url)
        elif platform == Platform.THREADS:
            return await self.extract_threads_post(url)
        else:
            raise ValueError(f"Plataforma não suportada: {platform}")

    async def extract_x_tweet(self, url: str) -> VideoMetadata:
        """Extrai metadata de tweet/post do X.com (Twitter) via apidojo/tweet-scraper"""
        print(f"🐦 Extraindo metadata do X/Twitter: {url}")

        try:
            client = self._get_next_client()

            # Tentar twitter-scraper-lite primeiro (suporta tweets individuais)
            # Fallback pra tweet-scraper se nao disponivel
            actor_name = "apidojo/twitter-scraper-lite"
            try:
                run = client.actor(actor_name).call(
                    run_input={
                        "startUrls": [{"url": url}],
                        "maxItems": 1,
                        "addUserInfo": True,
                    },
                    timeout_secs=120
                )
            except Exception:
                # Fallback: tweet-scraper com searchTerms
                import re as _re
                tweet_id_match = _re.search(r'/status/(\d+)', url)
                actor_name = "apidojo/tweet-scraper"
                run = client.actor(actor_name).call(
                    run_input={
                        "searchTerms": [url],
                        "maxItems": 1,
                        "addUserInfo": True,
                    },
                    timeout_secs=120
                )

            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            if not items:
                raise ValueError(f"X/Twitter scraper ({actor_name}) nao retornou dados")

            data = items[0]

            # Campos camelCase (formato Tweet Scraper V2)
            text = data.get("text") or data.get("full_text") or ""
            author_obj = data.get("author", {})
            author = author_obj.get("userName") or author_obj.get("screen_name") or data.get("user", {}).get("screen_name", "")

            hashtags = re.findall(r'#\w+', text)

            # Thumbnail: buscar em media arrays
            thumbnail_url = None
            media_list = data.get("media", []) or data.get("extendedEntities", {}).get("media", []) or []
            for m in media_list:
                thumb = m.get("media_url_https") or m.get("url") or m.get("media_url")
                if thumb:
                    thumbnail_url = thumb
                    break

            # Comentarios (replies)
            top_comments = []
            replies = data.get("replies", []) or []
            for r in replies[:50]:
                reply_text = r.get("text", "")
                if reply_text:
                    top_comments.append(Comment(
                        text=reply_text,
                        author=r.get("author", {}).get("userName", ""),
                        likes=r.get("likeCount", 0),
                    ))

            return VideoMetadata(
                url=url,
                platform=Platform.X,
                title=text[:100] + ("..." if len(text) > 100 else ""),
                description=text,
                hashtags=hashtags,
                views=data.get("viewCount") or data.get("views_count"),
                likes=data.get("likeCount") or data.get("favorite_count"),
                comments_count=data.get("replyCount") or data.get("reply_count"),
                top_comments=top_comments,
                thumbnail_url=thumbnail_url,
                duration=None,
                author=author,
                author_url=f"https://x.com/{author}" if author else None,
                published_at=data.get("createdAt") or data.get("created_at"),
            )

        except Exception as e:
            print(f"❌ Erro ao extrair X/Twitter: {str(e)}")
            return VideoMetadata(
                url=url,
                platform=Platform.X,
                title="X Post",
                description="",
                hashtags=[],
            )

    async def extract_threads_post(self, url: str) -> VideoMetadata:
        """Extrai metadata de post do Threads via automation-lab/threads-scraper"""
        print(f"🧵 Extraindo metadata do Threads: {url}")

        try:
            client = self._get_next_client()

            # Extrair username e post ID da URL
            import re as _re
            username_match = _re.search(r'threads\.(?:com|net)/@([^/]+)', url)
            post_id_match = _re.search(r'/post/([A-Za-z0-9_-]+)', url)
            username = username_match.group(1) if username_match else ""
            post_id = post_id_match.group(1) if post_id_match else ""

            run = client.actor("logical_scrapers/threads-post-scraper").call(
                run_input={
                    "post_urls": [url],
                },
                timeout_secs=120
            )

            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            if not items:
                raise ValueError("Threads scraper nao retornou dados")

            data = items[0]

            # Campos com prefixo "thread." (formato logical_scrapers)
            text = data.get("thread.text") or data.get("text") or ""
            author = data.get("thread.username") or data.get("username") or username

            hashtags = re.findall(r'#\w+', text)

            # Thumbnail: buscar em replies com imagens
            thumbnail_url = None
            # Replies com comentarios reais
            top_comments = []
            replies = data.get("replies") or []
            for r in replies[:50]:
                reply_text = r.get("text", "")
                if reply_text:
                    top_comments.append(Comment(
                        text=reply_text,
                        author=r.get("username", ""),
                        likes=r.get("like_count", 0),
                    ))
                # Pegar thumbnail da primeira imagem encontrada nas replies
                if not thumbnail_url:
                    reply_images = r.get("images") or []
                    if reply_images:
                        thumbnail_url = reply_images[0]

            return VideoMetadata(
                url=url,
                platform=Platform.THREADS,
                title=text[:100] + ("..." if len(text) > 100 else ""),
                description=text,
                hashtags=hashtags,
                views=data.get("thread.view_count") or data.get("viewCount"),
                likes=data.get("thread.like_count") or data.get("likeCount"),
                comments_count=data.get("thread.reply_count") or data.get("replyCount") or len(replies),
                top_comments=top_comments,
                thumbnail_url=thumbnail_url,
                duration=None,
                author=author,
                author_url=f"https://www.threads.com/@{author}" if author else None,
                published_at=data.get("thread.published_on") or data.get("timestamp"),
            )

        except Exception as e:
            print(f"❌ Erro ao extrair Threads: {str(e)}")
            return VideoMetadata(
                url=url,
                platform=Platform.THREADS,
                title="Threads Post",
                description="",
                hashtags=[],
            )

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

            # Função para executar scraping TikTok com um cliente específico
            async def run_tiktok_downloader(client: ApifyClient):
                run = client.actor("apify/tiktok-scraper").call(run_input=run_input)
                items = []
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)
                if not items:
                    raise ValueError("Vídeo do TikTok não encontrado")
                return items[0]

            # Tenta com todos os tokens disponíveis até conseguir
            data = await self._try_all_clients(run_tiktok_downloader, "extract_video_download_url_tiktok")

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

            # Função para executar scraping Instagram com um cliente específico
            async def run_instagram_downloader(client: ApifyClient):
                run = client.actor("apify/instagram-scraper").call(
                    run_input=run_input,
                    timeout_secs=120  # 2 minutos max
                )
                items = []
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)
                    break
                if not items:
                    raise ValueError("Instagram scraper retornou vazio")
                data = items[0]
                # Valida se tem videoUrl
                if not data.get("videoUrl"):
                    raise ValueError("Instagram scraper não retornou videoUrl")
                return data

            # Tenta com todos os tokens disponíveis até conseguir
            data = await self._try_all_clients(run_instagram_downloader, "extract_video_download_url_instagram")

            # Instagram retorna videoUrl no campo "videoUrl"
            video_url = data.get("videoUrl")

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

    async def extract_all_instagram_comments(
        self,
        post_url: str,
        max_comments: int = 1000
    ) -> List[Comment]:
        """
        Extrai TODOS os comentários de um post do Instagram usando o scraper dedicado.

        USO HÍBRIDO:
        - extract_instagram_reel() retorna ~6 comentários (preview rápido)
        - extract_all_instagram_comments() retorna TODOS os comentários (análise profunda)

        Args:
            post_url: URL do post do Instagram (https://www.instagram.com/p/...)
            max_comments: Máximo de comentários a extrair (default: 1000)

        Returns:
            Lista de Comment ordenados por likes (mais relevantes primeiro)

        Custo: $2.30 por 1,000 comentários extraídos
        Tempo: ~30-60s dependendo da quantidade
        """
        if not self.apify_token:
            raise ValueError("Apify token não configurado")

        print(f"🔄 Extraindo TODOS os comentários do post: {post_url}")
        print(f"   Limite: {max_comments} comentários")
        print(f"   Custo estimado: ${(max_comments / 1000) * 2.30:.2f}")

        try:
            run_input = {
                "directUrls": [post_url],
                "resultsLimit": max_comments,
            }

            # Executar Instagram Comments Scraper
            async def run_comments_scraper(client: ApifyClient):
                run = client.actor("apify/instagram-comment-scraper").call(
                    run_input=run_input,
                    timeout_secs=300  # 5 minutos max
                )
                items = []
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)
                return items

            # Tenta com todos os tokens disponíveis
            comments_data = await self._try_all_clients(run_comments_scraper, "extract_all_instagram_comments")

            # Converter para lista de Comment
            all_comments = []
            for comment_data in comments_data:
                all_comments.append(Comment(
                    text=comment_data.get("text", ""),
                    author=comment_data.get("ownerUsername", ""),
                    likes=comment_data.get("likesCount", 0)
                ))

            # Ordenar por likes (mais relevantes primeiro)
            all_comments.sort(key=lambda x: x.likes, reverse=True)

            print(f"✅ {len(all_comments)} comentários extraídos com sucesso!")
            print(f"   Top comentário: \"{all_comments[0].text[:60]}...\" ({all_comments[0].likes:,} likes)")

            return all_comments

        except Exception as e:
            print(f"❌ Erro ao extrair todos os comentários: {str(e)}")
            raise ValueError(f"Falha ao extrair comentários do Instagram: {str(e)}")

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()