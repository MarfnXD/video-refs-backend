"""
Script para processar 6 bookmarks específicos sem cloud_video_url
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

# IDs específicos
bookmark_ids = [
    'c88c9c45-6fb4-49dd-b5df-374a9adfac3f',
    'd644e177-0008-4361-ae51-98d747fb29e7',
    'bdaafbb9-954a-44ff-835e-c2729bd7d330',
    'cf21bb4e-73d9-4d2b-a29f-e4d56910a7a6',
    '5e1d65c0-68b6-49f9-8f46-1d83c3a034ae',
    'e75e0801-b8de-42af-a47a-57b500bb71bc'
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
            '-ss', '00:00:01.000',
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            temp_thumb
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"ffmpeg falhou: {result.stderr}")

        logger.info(f"   ✅ Frame extraído")

        # Upload da thumbnail para cloud
        logger.info(f"   ☁️  Fazendo upload da thumbnail...")

        with open(temp_thumb, 'rb') as f:
            thumb_bytes = f.read()

        cloud_path = f"{user_id}/thumbnails/{bookmark_id}.jpg"

        supabase.storage.from_("thumbnails").upload(
            path=cloud_path,
            file=thumb_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )

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
        if temp_video and os.path.exists(temp_video.name):
            os.remove(temp_video.name)
        if temp_thumb and os.path.exists(temp_thumb):
            os.remove(temp_thumb)

async def process_bookmark(bookmark_id: str, url: str, user_id: str, title: str) -> bool:
    """
    Processa um bookmark: baixa vídeo via Apify, faz upload e gera thumbnail
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"📹 {title[:60]}")
    logger.info(f"   ID: {bookmark_id[:8]}")
    logger.info(f"   URL: {url}")

    try:
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
                raise Exception(f"Apify não retornou nem video_path nem download_url")

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
            'cloud_video_url': cloud_video_url,
            'processing_status': 'completed',
            'ai_processed': True
        }).eq('id', bookmark_id).execute()

        # Cleanup do arquivo local
        if os.path.exists(video_path):
            os.remove(video_path)

        logger.info(f"✅ SUCESSO! Vídeo salvo (thumbnail já existe)")
        return True

    except Exception as e:
        logger.error(f"❌ ERRO: {str(e)}")
        return False

async def main():
    # Buscar dados dos bookmarks
    result = supabase.table('bookmarks').select('id, smart_title, url, user_id').in_('id', bookmark_ids).execute()

    bookmarks = result.data

    logger.info("="*80)
    logger.info("🚀 Processamento de 6 Bookmarks sem cloud_video_url")
    logger.info(f"   Total: {len(bookmarks)} bookmarks")
    logger.info("="*80)

    success_count = 0
    fail_count = 0

    for i, bm in enumerate(bookmarks, 1):
        logger.info(f"\n[{i}/{len(bookmarks)}]")

        title = bm.get('smart_title') or 'Sem título'

        if await process_bookmark(bm['id'], bm['url'], bm['user_id'], title):
            success_count += 1
        else:
            fail_count += 1

        # Pequena pausa entre processamentos
        if i < len(bookmarks):
            logger.info(f"\n   ⏸️  Aguardando 3s antes do próximo...")
            await asyncio.sleep(3)

    logger.info("\n" + "="*80)
    logger.info(f"🏁 CONCLUÍDO!")
    logger.info(f"   ✅ Sucesso: {success_count}")
    logger.info(f"   ❌ Falhas: {fail_count}")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(main())
