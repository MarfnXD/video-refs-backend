"""
Servico de embeddings usando Gemini Embedding 2 (multimodal)

Gera vetores de 768 dimensoes capturando significado semantico.
Suporta embedding multimodal (video, imagem) e texto.

Modelo: gemini-embedding-2-preview (768 dimensoes, multimodal)
- Imagens: baixa bytes e envia como inline_data (base64)
- Videos: upload via Gemini File API, espera ACTIVE, usa file_uri
- Texto: envia direto
"""
import os
import logging
import base64
import asyncio
import httpx
from typing import Optional, List

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_UPLOAD_BASE = "https://generativelanguage.googleapis.com/upload/v1beta"
MODEL_NAME = "gemini-embedding-2-preview"
OUTPUT_DIMENSIONS = 768


class EmbeddingService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY nao configurada - Embedding service desabilitado")

    @property
    def is_available(self) -> bool:
        return self.api_key is not None

    def _embed_url(self) -> str:
        return f"{GEMINI_API_BASE}/models/{MODEL_NAME}:embedContent?key={self.api_key}"

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """Gera embedding de texto puro (768d)."""
        if not self.is_available or not text or not text.strip():
            return None

        try:
            payload = {
                "model": f"models/{MODEL_NAME}",
                "content": {"parts": [{"text": text}]},
                "outputDimensionality": OUTPUT_DIMENSIONS,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self._embed_url(), json=payload)
                resp.raise_for_status()

            embedding = resp.json().get("embedding", {}).get("values", [])
            if embedding:
                logger.info(f"Embedding texto gerado - {len(embedding)} dims, {len(text)} chars")
            return embedding or None

        except Exception as e:
            logger.error(f"Erro embedding texto: {str(e)}")
            return None

    async def embed_image(self, image_url: str) -> Optional[List[float]]:
        """
        Baixa imagem de URL externa e gera embedding via inline_data (base64).
        Funciona com qualquer URL publica (Supabase, Instagram CDN, etc).
        """
        if not self.is_available or not image_url:
            return None

        try:
            # Baixar imagem
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()

            image_bytes = resp.content
            content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
            logger.info(f"Imagem baixada: {len(image_bytes)} bytes, {content_type}")

            # Embedding via inline_data (base64)
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            payload = {
                "model": f"models/{MODEL_NAME}",
                "content": {
                    "parts": [{
                        "inline_data": {
                            "mime_type": content_type,
                            "data": b64,
                        }
                    }]
                },
                "outputDimensionality": OUTPUT_DIMENSIONS,
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self._embed_url(), json=payload)
                resp.raise_for_status()

            embedding = resp.json().get("embedding", {}).get("values", [])
            if embedding:
                logger.info(f"Embedding IMAGEM gerado - {len(embedding)} dims")
            return embedding or None

        except Exception as e:
            logger.error(f"Erro embedding imagem: {str(e)}")
            return None

    async def embed_video(self, video_url: str) -> Optional[List[float]]:
        """
        Baixa video de URL externa, faz upload na Gemini File API,
        espera ACTIVE, e gera embedding multimodal (768d).
        Limite: 120s de video.
        """
        if not self.is_available or not video_url:
            return None

        try:
            # 1. Baixar video
            logger.info(f"Baixando video pra embedding: {video_url[:60]}...")
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(video_url)
                resp.raise_for_status()

            video_bytes = resp.content
            logger.info(f"Video baixado: {len(video_bytes)} bytes ({len(video_bytes)/1024/1024:.1f}MB)")

            # Limite: 100MB por request
            if len(video_bytes) > 100 * 1024 * 1024:
                logger.warning("Video muito grande pra embedding (>100MB)")
                return None

            # 2. Upload na Gemini File API
            file_uri = await self._upload_to_file_api(video_bytes, "video/mp4")

            # 3. Gerar embedding com file_data
            payload = {
                "model": f"models/{MODEL_NAME}",
                "content": {
                    "parts": [{
                        "file_data": {
                            "mime_type": "video/mp4",
                            "file_uri": file_uri,
                        }
                    }]
                },
                "outputDimensionality": OUTPUT_DIMENSIONS,
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(self._embed_url(), json=payload)
                resp.raise_for_status()

            embedding = resp.json().get("embedding", {}).get("values", [])
            if embedding:
                logger.info(f"Embedding VIDEO gerado - {len(embedding)} dims")
            return embedding or None

        except Exception as e:
            logger.error(f"Erro embedding video: {str(e)}")
            return None

    async def _upload_to_file_api(self, file_bytes: bytes, mime_type: str) -> str:
        """Upload resumable na Gemini File API. Retorna file_uri."""
        num_bytes = len(file_bytes)

        # Iniciar upload resumable
        init_url = f"{GEMINI_UPLOAD_BASE}/files?key={self.api_key}"
        headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(num_bytes),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(init_url, headers=headers, json={"file": {"display_name": "embed_video"}})
            resp.raise_for_status()

        upload_url = resp.headers.get("x-goog-upload-url")
        if not upload_url:
            raise ValueError("Gemini File API nao retornou upload URL")

        # Enviar bytes
        upload_headers = {
            "Content-Length": str(num_bytes),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(upload_url, headers=upload_headers, content=file_bytes)
            resp.raise_for_status()

        file_info = resp.json()
        file_uri = file_info["file"]["uri"]
        file_name = file_info["file"]["name"]
        state = file_info["file"].get("state", "ACTIVE")

        logger.info(f"File API upload OK: {file_name}, state={state}")

        # Esperar processamento se necessario
        if state == "PROCESSING":
            file_uri = await self._wait_for_active(file_name)

        return file_uri

    async def _wait_for_active(self, file_name: str, max_wait: int = 120) -> str:
        """Polling ate arquivo ficar ACTIVE na File API."""
        check_url = f"{GEMINI_API_BASE}/{file_name}?key={self.api_key}"
        elapsed = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            while elapsed < max_wait:
                resp = await client.get(check_url)
                resp.raise_for_status()
                info = resp.json()
                state = info.get("state", "UNKNOWN")

                if state == "ACTIVE":
                    return info["uri"]
                elif state == "FAILED":
                    raise RuntimeError(f"File API processamento falhou: {info}")

                await asyncio.sleep(3)
                elapsed += 3

        raise TimeoutError(f"File API nao ficou ACTIVE em {max_wait}s")

    def _build_text_from_bookmark(self, bookmark: dict) -> str:
        """Combina campos do bookmark em texto para embedding."""
        parts = []

        smart_title = bookmark.get('smart_title')
        if smart_title:
            parts.append(smart_title)
            parts.append(smart_title)  # 2x peso

        auto_tags = bookmark.get('auto_tags')
        if auto_tags and isinstance(auto_tags, list):
            parts.append(", ".join(auto_tags))

        auto_categories = bookmark.get('auto_categories')
        if auto_categories and isinstance(auto_categories, list):
            parts.append(", ".join(auto_categories))

        transcript = bookmark.get('video_transcript')
        if transcript:
            parts.append(str(transcript)[:500])

        visual = bookmark.get('visual_analysis')
        if visual:
            parts.append(str(visual)[:500])

        return " | ".join(filter(None, parts))

    async def generate_embedding(self, bookmark: dict) -> Optional[List[float]]:
        """
        Gera embedding para bookmark. Prioridade:
        1. Video multimodal (baixa + File API + embed)
        2. Imagem multimodal (baixa + inline_data base64)
        3. Texto (smart_title + tags + transcript)
        """
        cloud_video_url = bookmark.get('cloud_video_url')
        image_urls = bookmark.get('image_urls', [])

        # 1. Video multimodal
        if cloud_video_url:
            logger.info("Tentando embedding multimodal (video)...")
            embedding = await self.embed_video(cloud_video_url)
            if embedding:
                return embedding
            logger.warning("Embedding video falhou, tentando alternativas")

        # 2. Imagem multimodal
        if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
            logger.info("Tentando embedding multimodal (imagem)...")
            embedding = await self.embed_image(image_urls[0])
            if embedding:
                return embedding
            logger.warning("Embedding imagem falhou, fallback texto")

        # 3. Texto
        combined_text = self._build_text_from_bookmark(bookmark)
        if not combined_text:
            logger.warning("Nenhum conteudo pra embedding")
            return None

        return await self.embed_text(combined_text)

    async def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Embedding pra query de busca (mesmo modelo = mesmo espaco vetorial)."""
        return await self.embed_text(query)


# Singleton
embedding_service = EmbeddingService()
