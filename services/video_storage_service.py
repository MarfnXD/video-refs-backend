"""
Serviço para download e upload de vídeos para Supabase Storage

Fluxo:
1. Baixa vídeo do Instagram/TikTok/YouTube usando URL do Apify
2. Upload para Supabase Storage (bucket: user-videos)
3. Gera URL pública/signed (1 ano de validade)
4. Deleta arquivo temporário local
"""
import os
import logging
import tempfile
import httpx
from pathlib import Path
from typing import Optional, Tuple
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class VideoStorageService:
    def __init__(self):
        # Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.bucket_name = "user-videos"

    async def download_and_upload_video(
        self,
        video_url: str,
        user_id: str,
        bookmark_id: str
    ) -> Optional[Tuple[str, str]]:
        """
        Baixa vídeo e faz upload para Supabase Storage

        Args:
            video_url: URL direta do vídeo (do Apify)
            user_id: ID do usuário (para path no storage)
            bookmark_id: ID do bookmark (para nome do arquivo)

        Returns:
            Tuple[cloud_url, local_path] ou None se falhar
            - cloud_url: URL assinada do vídeo no Supabase (1 ano validade)
            - local_path: Path temporário local (para Gemini usar)
        """
        temp_file = None

        try:
            # 1. Criar arquivo temporário
            logger.info(f"📥 Baixando vídeo de: {video_url[:50]}...")

            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.mp4',
                dir='/tmp'
            )
            temp_path = temp_file.name
            temp_file.close()

            # 2. Baixar vídeo
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout
                async with client.stream('GET', video_url) as response:
                    response.raise_for_status()

                    total_size = 0
                    with open(temp_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            total_size += len(chunk)

            file_size_mb = total_size / (1024 * 1024)
            logger.info(f"✅ Vídeo baixado: {file_size_mb:.2f} MB")

            # 3. Upload para Supabase Storage
            logger.info(f"☁️ Fazendo upload para Supabase Storage...")

            # Path no storage: {user_id}/{bookmark_id}.mp4
            storage_path = f"{user_id}/{bookmark_id}.mp4"

            with open(temp_path, 'rb') as f:
                video_data = f.read()

            # Upload
            upload_response = self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=video_data,
                file_options={"content-type": "video/mp4"}
            )

            logger.info(f"✅ Upload concluído: {storage_path}")

            # 4. Gerar URL assinada (1 ano de validade)
            signed_url_response = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=storage_path,
                expires_in=31536000  # 1 ano em segundos
            )

            cloud_url = signed_url_response.get('signedURL')

            if not cloud_url:
                logger.error("❌ Erro ao gerar URL assinada")
                return None

            logger.info(f"✅ URL assinada gerada: {cloud_url[:50]}...")

            # Retornar URL da cloud + path temporário local
            return (cloud_url, temp_path)

        except Exception as e:
            logger.error(f"❌ Erro ao baixar/upload vídeo: {str(e)}", exc_info=True)

            # Limpar arquivo temporário se erro
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

            return None

    def cleanup_temp_file(self, temp_path: str):
        """
        Deleta arquivo temporário

        Args:
            temp_path: Path do arquivo temporário
        """
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.info(f"🗑️ Arquivo temporário deletado: {temp_path}")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao deletar arquivo temporário: {str(e)}")
