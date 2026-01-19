"""
Script síncrono para reprocessar bookmarks sem thumbnail
Contorna problemas do Celery/Tokio rodando de forma direta e sequencial
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client
import logging
import asyncio
import subprocess
import tempfile
import httpx
from typing import Optional

# Services
from services.apify_service import ApifyService
from services.gemini_service import gemini_service
from services.thumbnail_service import ThumbnailService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("Supabase credentials não configuradas")

# Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
apify_service = ApifyService()
thumbnail_service = ThumbnailService(supabase)

# IDs dos bookmarks (apenas o que conseguiu extrair via Apify)
bookmark_ids = [
    '2a6a9138-a57c-4c32-8a0c-30aa124087a8',  # F1 2024 (sem vídeo e thumb, mas Apify conseguiu download_url)
]

async def generate_thumbnail_from_video(cloud_video_url: str, user_id: str, bookmark_id: str) -> Optional[str]:
    """
    Gera thumbnail a partir de um vídeo na cloud usando ffmpeg
    """
    temp_video = None
    temp_thumb = None

    try:
        logger.info(f"   📥 Baixando vídeo da cloud...")

        # Baixar vídeo da cloud
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(cloud_video_url)
            response.raise_for_status()

            # Salvar em arquivo temporário
            temp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            temp_video.write(response.content)
            temp_video.close()

        logger.info(f"   ✅ Vídeo baixado: {len(response.content) / 1024 / 1024:.1f}MB")

        # Gerar thumbnail usando ffmpeg (frame do segundo 1)
        temp_thumb_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        temp_thumb = temp_thumb_file.name
        temp_thumb_file.close()

        logger.info(f"   🎬 Extraindo frame com ffmpeg...")

        result = subprocess.run([
            'ffmpeg',
            '-i', temp_video.name,
            '-ss', '00:00:01.000',  # Pegar frame do segundo 1
            '-vframes', '1',  # Apenas 1 frame
            '-q:v', '2',  # Qualidade alta
            '-y',  # Sobrescrever
            temp_thumb
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"ffmpeg falhou: {result.stderr}")

        logger.info(f"   ✅ Frame extraído")

        # Upload da thumbnail para cloud
        logger.info(f"   ☁️  Fazendo upload da thumbnail...")

        # Ler arquivo da thumbnail
        with open(temp_thumb, 'rb') as f:
            thumb_bytes = f.read()

        # Path na cloud
        cloud_path = f"{user_id}/thumbnails/{bookmark_id}.jpg"

        # Upload para Supabase
        supabase.storage.from_("thumbnails").upload(
            path=cloud_path,
            file=thumb_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )

        # Gerar signed URL (1 ano)
        signed_url = supabase.storage.from_("thumbnails").create_signed_url(
            path=cloud_path,
            expires_in=31536000
        )

        if signed_url and "signedURL" in signed_url:
            thumbnail_url = signed_url["signedURL"]
            logger.info(f"   ✅ Thumbnail no cloud: {thumbnail_url[:50]}...")
            return thumbnail_url
        else:
            raise Exception("Falha ao gerar signed URL")

    except Exception as e:
        logger.error(f"   ❌ Erro ao gerar thumbnail: {str(e)}")
        return None

    finally:
        # Cleanup
        if temp_video and os.path.exists(temp_video.name):
            os.remove(temp_video.name)
        if temp_thumb and os.path.exists(temp_thumb):
            os.remove(temp_thumb)

async def process_bookmark(bookmark_id: str) -> bool:
    """
    Processa um bookmark: gera thumbnail (com ou sem vídeo existente)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"📹 Processando bookmark: {bookmark_id}")

    # 1. Buscar dados do bookmark
    response = supabase.table('bookmarks').select('url, user_id, smart_title, cloud_video_url').eq('id', bookmark_id).single().execute()

    if not response.data:
        logger.error(f"❌ Bookmark não encontrado")
        return False

    bookmark = response.data
    url = bookmark.get('url')
    user_id = bookmark.get('user_id')
    title = bookmark.get('smart_title') or 'Sem título'
    cloud_video_url = bookmark.get('cloud_video_url')

    logger.info(f"   Título: {title[:60]}")
    logger.info(f"   URL: {url}")
    logger.info(f"   Tem vídeo: {bool(cloud_video_url)}")

    if not url or not user_id:
        logger.error(f"❌ Faltam dados (url ou user_id)")
        return False

    try:
        thumbnail_url = None

        # CASO 1: Já tem vídeo na cloud → gerar thumbnail direto do vídeo
        if cloud_video_url:
            logger.info(f"   ✅ Vídeo já existe na cloud, gerando thumbnail...")
            thumbnail_url = await generate_thumbnail_from_video(cloud_video_url, user_id, bookmark_id)

        # CASO 2: Não tem vídeo → baixar via Apify, fazer upload e gerar thumbnail
        else:
            logger.info(f"   ⚠️  Sem vídeo na cloud, baixando via Apify...")

            # Extrair URL de download via Apify (Instagram)
            result = await apify_service.extract_video_download_url_instagram(url, quality="720p")

            if not result:
                raise Exception("Apify não retornou resultado")

            # Pode retornar `video_path` (já baixado) ou `download_url` (precisa baixar)
            video_path = result.get('video_path')

            if not video_path:
                # Precisa baixar do download_url
                download_url = result.get('download_url')

                if not download_url:
                    raise Exception(f"Apify não retornou nem video_path nem download_url: {result}")

                logger.info(f"   📥 Baixando vídeo de: {download_url[:60]}...")

                # Baixar vídeo
                async with httpx.AsyncClient(timeout=180.0) as client:
                    response = await client.get(download_url)
                    response.raise_for_status()

                    # Salvar temporariamente
                    temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                    temp_file.write(response.content)
                    temp_file.close()
                    video_path = temp_file.name

                logger.info(f"   ✅ Vídeo baixado: {len(response.content) / 1024 / 1024:.1f}MB")
            else:
                logger.info(f"   ✅ Vídeo já baixado: {video_path}")

            # Upload para Supabase Storage (vídeo)
            logger.info(f"   ☁️  Fazendo upload do vídeo...")

            # Ler vídeo
            with open(video_path, 'rb') as f:
                video_bytes = f.read()

            # Path na cloud
            video_cloud_path = f"{user_id}/videos/{bookmark_id}.mp4"

            # Upload
            supabase.storage.from_("user-videos").upload(
                path=video_cloud_path,
                file=video_bytes,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )

            # Gerar signed URL para vídeo
            signed_video = supabase.storage.from_("user-videos").create_signed_url(
                path=video_cloud_path,
                expires_in=31536000
            )

            if not signed_video or "signedURL" not in signed_video:
                raise Exception("Falha ao gerar signed URL do vídeo")

            cloud_video_url = signed_video["signedURL"]
            logger.info(f"   ✅ Vídeo no cloud: {cloud_video_url[:50]}...")

            # Atualizar cloud_video_url no banco
            supabase.table('bookmarks').update({
                'cloud_video_url': cloud_video_url
            }).eq('id', bookmark_id).execute()

            # Gerar thumbnail do vídeo baixado
            logger.info(f"   🖼️  Gerando thumbnail do vídeo...")
            thumbnail_url = await generate_thumbnail_from_video(cloud_video_url, user_id, bookmark_id)

            # Cleanup do arquivo local
            if os.path.exists(video_path):
                os.remove(video_path)

        # Verificar se thumbnail foi gerada
        if not thumbnail_url:
            raise Exception("Falha ao gerar thumbnail")

        # Atualizar bookmark com thumbnail
        supabase.table('bookmarks').update({
            'cloud_thumbnail_url': thumbnail_url,
            'ai_processed': True
        }).eq('id', bookmark_id).execute()

        logger.info(f"✅ SUCESSO! Thumbnail gerada e salva")
        return True

    except Exception as e:
        logger.error(f"❌ ERRO: {str(e)}")
        return False

async def main():
    logger.info("="*80)
    logger.info("🚀 Processamento Síncrono de Bookmarks sem Thumbnail")
    logger.info(f"   Total: {len(bookmark_ids)} bookmarks")
    logger.info("="*80)

    success_count = 0
    fail_count = 0

    for i, bookmark_id in enumerate(bookmark_ids, 1):
        logger.info(f"\n[{i}/{len(bookmark_ids)}]")

        if await process_bookmark(bookmark_id):
            success_count += 1
        else:
            fail_count += 1

        # Pequena pausa entre processamentos
        if i < len(bookmark_ids):
            logger.info(f"\n   ⏸️  Aguardando 2s antes do próximo...")
            await asyncio.sleep(2)

    logger.info("\n" + "="*80)
    logger.info(f"🏁 CONCLUÍDO!")
    logger.info(f"   ✅ Sucesso: {success_count}")
    logger.info(f"   ❌ Falhas: {fail_count}")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(main())
