"""
Servico de embeddings usando Gemini Embedding 2 (multimodal)

Gera vetores de 768 dimensoes capturando significado semantico.
Suporta embedding multimodal (video direto) e texto.

Modelo: gemini-embedding-2-preview (768 dimensoes, multimodal)
Custo: ~$0.20 por 1M tokens texto, ~$12/M tokens video
"""
import os
import logging
import httpx
from typing import Optional, List

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
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

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Gera embedding de texto puro via Gemini Embed 2.

        Args:
            text: Texto combinado para embeddar

        Returns:
            Lista de 768 floats ou None se falhar
        """
        if not self.is_available:
            logger.error("Embedding service nao disponivel (GEMINI_API_KEY faltando)")
            return None

        if not text or not text.strip():
            logger.warning("Texto vazio para embedding")
            return None

        try:
            url = f"{GEMINI_API_BASE}/models/{MODEL_NAME}:embedContent?key={self.api_key}"

            payload = {
                "model": f"models/{MODEL_NAME}",
                "content": {
                    "parts": [{"text": text}]
                },
                "outputDimensionality": OUTPUT_DIMENSIONS
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding", {}).get("values", [])

            if not embedding:
                logger.error(f"Resposta sem embedding: {data}")
                return None

            logger.info(f"Embedding texto gerado - {len(embedding)} dims, {len(text)} chars input")
            return embedding

        except Exception as e:
            logger.error(f"Erro ao gerar embedding texto: {str(e)}")
            return None

    async def embed_video(self, video_url: str) -> Optional[List[float]]:
        """
        Gera embedding multimodal de video via Gemini Embed 2.
        O video e referenciado por URL (Supabase Storage signed URL).
        Limite: 120 segundos de video.

        Args:
            video_url: URL publica do video (cloud_video_url do Supabase)

        Returns:
            Lista de 768 floats ou None se falhar
        """
        if not self.is_available:
            logger.error("Embedding service nao disponivel (GEMINI_API_KEY faltando)")
            return None

        if not video_url:
            logger.warning("URL de video vazia para embedding")
            return None

        try:
            url = f"{GEMINI_API_BASE}/models/{MODEL_NAME}:embedContent?key={self.api_key}"

            payload = {
                "model": f"models/{MODEL_NAME}",
                "content": {
                    "parts": [{
                        "fileData": {
                            "mimeType": "video/mp4",
                            "fileUri": video_url
                        }
                    }]
                },
                "outputDimensionality": OUTPUT_DIMENSIONS
            }

            # Video embedding pode demorar mais
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding", {}).get("values", [])

            if not embedding:
                logger.error(f"Resposta sem embedding video: {data}")
                return None

            logger.info(f"Embedding VIDEO gerado - {len(embedding)} dims")
            return embedding

        except Exception as e:
            logger.error(f"Erro ao gerar embedding video: {str(e)}")
            return None

    def _build_text_from_bookmark(self, bookmark: dict) -> str:
        """
        Combina campos do bookmark em texto para embedding.
        Prioridade: smart_title (2x) > auto_tags > auto_categories > transcript > visual_analysis
        """
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

    async def embed_image(self, image_url: str) -> Optional[List[float]]:
        """
        Gera embedding multimodal de uma imagem via Gemini Embed 2.

        Args:
            image_url: URL publica da imagem

        Returns:
            Lista de 768 floats ou None
        """
        if not self.is_available or not image_url:
            return None

        try:
            url = f"{GEMINI_API_BASE}/models/{MODEL_NAME}:embedContent?key={self.api_key}"

            payload = {
                "model": f"models/{MODEL_NAME}",
                "content": {
                    "parts": [{
                        "fileData": {
                            "mimeType": "image/jpeg",
                            "fileUri": image_url
                        }
                    }]
                },
                "outputDimensionality": OUTPUT_DIMENSIONS
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding", {}).get("values", [])

            if embedding:
                logger.info(f"Embedding IMAGEM gerado - {len(embedding)} dims")
            return embedding or None

        except Exception as e:
            logger.error(f"Erro ao gerar embedding imagem: {str(e)}")
            return None

    async def generate_embedding(self, bookmark: dict) -> Optional[List[float]]:
        """
        Gera embedding para um bookmark. Prioridade:
        1. Video multimodal (se tem cloud_video_url)
        2. Imagem multimodal (se tem image_urls de carousel)
        3. Texto (smart_title + tags + transcript)
        """
        cloud_video_url = bookmark.get('cloud_video_url')
        image_urls = bookmark.get('image_urls', [])

        # 1. Tentar embedding multimodal (video direto)
        if cloud_video_url:
            logger.info("Tentando embedding multimodal (video direto)...")
            embedding = await self.embed_video(cloud_video_url)
            if embedding:
                return embedding
            logger.warning("Embedding video falhou, tentando alternativas")

        # 2. Tentar embedding multimodal (imagem)
        if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
            logger.info(f"Tentando embedding multimodal (imagem)...")
            embedding = await self.embed_image(image_urls[0])
            if embedding:
                return embedding
            logger.warning("Embedding imagem falhou, fazendo fallback para texto")

        # 3. Fallback: embedding de texto
        combined_text = self._build_text_from_bookmark(bookmark)
        if not combined_text:
            logger.warning("Nenhum conteudo disponivel para embedding")
            return None

        return await self.embed_text(combined_text)

    async def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Gera embedding para uma query de busca.
        Usa o mesmo modelo para garantir compatibilidade no espaco vetorial.

        Args:
            query: Texto da busca do usuario

        Returns:
            Lista de 768 floats ou None
        """
        return await self.embed_text(query)


# Singleton
embedding_service = EmbeddingService()
