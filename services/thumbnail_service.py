"""
Serviço para gerenciar upload de thumbnails para Supabase Storage

Responsabilidades:
- Baixar imagem de thumbnail de URL externa (YouTube, Instagram, TikTok)
- Fazer upload para Supabase Storage
- Gerar signed URL válida por 1 ano
- Path structure: {userId}/thumbnails/{bookmarkId}.jpg
"""

import httpx
import logging
from typing import Optional, Dict
from supabase import Client
import os

logger = logging.getLogger(__name__)


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
        Baixa thumbnail de URL externa e faz upload para Supabase Storage

        Args:
            thumbnail_url: URL da thumbnail original (YouTube, Instagram, etc)
            user_id: ID do usuário (para path)
            bookmark_id: ID do bookmark (para nome do arquivo)

        Returns:
            URL permanente da thumbnail no Supabase Storage (signed URL válida por 1 ano)
            ou None se falhar
        """
        try:
            logger.info(f"📸 Iniciando upload de thumbnail para bookmark {bookmark_id}")
            logger.debug(f"URL original: {thumbnail_url[:80]}...")

            # 1. Baixar imagem da URL original
            logger.debug("⬇️ Baixando imagem da URL original...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(thumbnail_url)
                response.raise_for_status()
                image_bytes = response.content

            logger.info(f"✅ Imagem baixada: {len(image_bytes) / 1024:.1f}KB")

            # 2. Determinar extensão (geralmente .jpg, mas pode ser .webp)
            content_type = response.headers.get("content-type", "image/jpeg")
            extension = self._get_extension_from_content_type(content_type)
            logger.debug(f"Tipo de conteúdo: {content_type}, extensão: {extension}")

            # 3. Path na cloud: {userId}/thumbnails/{bookmarkId}.jpg
            cloud_path = f"{user_id}/thumbnails/{bookmark_id}{extension}"
            logger.debug(f"Cloud path: {cloud_path}")

            # 4. Upload para Supabase Storage
            logger.debug("☁️ Fazendo upload para Supabase Storage...")
            self.supabase.storage.from_(self.bucket_name).upload(
                path=cloud_path,
                file=image_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            logger.info(f"✅ Upload concluído para: {cloud_path}")

            # 5. Gerar signed URL válida por 1 ano (31536000 segundos)
            logger.debug("🔑 Gerando signed URL (válida por 1 ano)...")
            signed_url = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=cloud_path,
                expires_in=31536000  # 1 ano em segundos
            )

            if signed_url and "signedURL" in signed_url:
                final_url = signed_url["signedURL"]
                logger.info(f"✅ Signed URL gerada: {final_url[:80]}...")
                return final_url
            else:
                logger.error("❌ Falha ao gerar signed URL")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Erro HTTP ao baixar thumbnail: {e.response.status_code}")
            return None
        except httpx.TimeoutException:
            logger.error("❌ Timeout ao baixar thumbnail")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao fazer upload de thumbnail: {str(e)}")
            logger.exception(e)
            return None

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
