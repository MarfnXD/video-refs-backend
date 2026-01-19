"""
Serviço para gerenciar upload de thumbnails para Supabase Storage

Responsabilidades:
- Baixar imagem de thumbnail de URL externa (YouTube, Instagram, TikTok)
- Fazer upload para Supabase Storage
- Gerar signed URL válida por 1 ano
- Path structure: {userId}/thumbnails/{bookmarkId}.jpg

Melhorias v2:
- Retry com backoff exponencial (3 tentativas)
- Timeout no upload pro Supabase
- Logs detalhados para debug
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict
from supabase import Client
import os

logger = logging.getLogger(__name__)

# Configurações de retry
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # segundos
DOWNLOAD_TIMEOUT = 30  # segundos
UPLOAD_TIMEOUT = 60  # segundos


class ThumbnailService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.bucket_name = "thumbnails"  # Bucket específico para thumbnails (aceita imagens)

    async def upload_thumbnail(
        self,
        thumbnail_url: str,
        user_id: str,
        bookmark_id: str
    ) -> Optional[str]:
        """
        Baixa thumbnail de URL externa e faz upload para Supabase Storage.
        Implementa retry com backoff exponencial.

        Args:
            thumbnail_url: URL da thumbnail original (YouTube, Instagram, etc)
            user_id: ID do usuário (para path)
            bookmark_id: ID do bookmark (para nome do arquivo)

        Returns:
            URL permanente da thumbnail no Supabase Storage (signed URL válida por 1 ano)
            ou None se falhar após todas as tentativas
        """
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📸 [{bookmark_id[:8]}] Tentativa {attempt}/{MAX_RETRIES} - Upload de thumbnail")

                result = await self._do_upload(thumbnail_url, user_id, bookmark_id)

                if result:
                    if attempt > 1:
                        logger.info(f"✅ [{bookmark_id[:8]}] Sucesso na tentativa {attempt}")
                    return result

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ [{bookmark_id[:8]}] Tentativa {attempt} falhou: {type(e).__name__}: {str(e)[:100]}")

                if attempt < MAX_RETRIES:
                    backoff = INITIAL_BACKOFF * (2 ** (attempt - 1))  # 2s, 4s, 8s
                    logger.info(f"⏳ [{bookmark_id[:8]}] Aguardando {backoff}s antes de retry...")
                    await asyncio.sleep(backoff)

        logger.error(f"❌ [{bookmark_id[:8]}] Falhou após {MAX_RETRIES} tentativas. Último erro: {last_error}")
        return None

    async def _do_upload(
        self,
        thumbnail_url: str,
        user_id: str,
        bookmark_id: str
    ) -> Optional[str]:
        """
        Executa o upload de uma thumbnail (uma tentativa).
        """
        # 1. Baixar imagem da URL original
        logger.debug(f"⬇️ [{bookmark_id[:8]}] Baixando imagem: {thumbnail_url[:60]}...")

        async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
            response = await client.get(thumbnail_url, follow_redirects=True)
            response.raise_for_status()
            image_bytes = response.content

        size_kb = len(image_bytes) / 1024
        logger.info(f"✅ [{bookmark_id[:8]}] Imagem baixada: {size_kb:.1f}KB")

        # 2. Determinar extensão
        content_type = response.headers.get("content-type", "image/jpeg")
        extension = self._get_extension_from_content_type(content_type)

        # 3. Path na cloud
        cloud_path = f"{user_id}/thumbnails/{bookmark_id}{extension}"

        # 4. Upload para Supabase Storage (com timeout via asyncio)
        logger.debug(f"☁️ [{bookmark_id[:8]}] Upload para Supabase: {cloud_path}")

        try:
            # Executa upload síncrono com timeout
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.supabase.storage.from_(self.bucket_name).upload(
                        path=cloud_path,
                        file=image_bytes,
                        file_options={"content-type": content_type, "upsert": "true"}
                    )
                ),
                timeout=UPLOAD_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise Exception(f"Timeout ({UPLOAD_TIMEOUT}s) no upload para Supabase")

        logger.info(f"✅ [{bookmark_id[:8]}] Upload concluído: {cloud_path}")

        # 5. Gerar signed URL válida por 1 ano
        logger.debug(f"🔑 [{bookmark_id[:8]}] Gerando signed URL...")

        signed_url = self.supabase.storage.from_(self.bucket_name).create_signed_url(
            path=cloud_path,
            expires_in=31536000  # 1 ano
        )

        if signed_url and "signedURL" in signed_url:
            final_url = signed_url["signedURL"]
            logger.info(f"✅ [{bookmark_id[:8]}] Signed URL OK: {final_url[:60]}...")
            return final_url
        else:
            raise Exception("Falha ao gerar signed URL")

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Retorna extensão de arquivo baseada no content-type"""
        if "webp" in content_type.lower():
            return ".webp"
        elif "png" in content_type.lower():
            return ".png"
        else:
            return ".jpg"  # Default

    async def delete_thumbnail(self, user_id: str, bookmark_id: str) -> bool:
        """
        Deleta thumbnail do Supabase Storage

        Args:
            user_id: ID do usuário
            bookmark_id: ID do bookmark

        Returns:
            True se deletado com sucesso, False caso contrário
        """
        try:
            # Tenta deletar com as 3 extensões possíveis
            for ext in [".jpg", ".webp", ".png"]:
                cloud_path = f"{user_id}/thumbnails/{bookmark_id}{ext}"
                try:
                    self.supabase.storage.from_(self.bucket_name).remove([cloud_path])
                    logger.info(f"🗑️ Thumbnail deletada: {cloud_path}")
                    return True
                except:
                    continue  # Tenta próxima extensão

            logger.warning(f"⚠️ Thumbnail não encontrada para bookmark {bookmark_id}")
            return False

        except Exception as e:
            logger.error(f"❌ Erro ao deletar thumbnail: {str(e)}")
            return False
