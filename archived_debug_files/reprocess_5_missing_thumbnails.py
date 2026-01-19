"""
Script para reprocessar 5 bookmarks específicos que estão sem thumbnail
Re-faz todo o pipeline: Apify download → Gemini análise → Claude processamento
"""
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client
from celery_app import celery_app
from tasks import process_bookmark_task
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY não configurada")

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# IDs dos bookmarks sem thumbnail
bookmark_ids = [
    '7c91f5ca-910b-4eda-b2ad-828c2f5f4e6e',  # Travis Scott x Nike Ad
    'd35673ee-a112-48fe-9bf1-bafa3248d08d',  # Red Bull x Arcane
    '0223b7a0-8f46-4f16-b365-a7bbd5d6929d',  # App Instories
    '4a5d996b-4ac8-432c-b1f7-7beb1d3ee2ac',  # Sem título (sem vídeo)
    '2a6a9138-a57c-4c32-8a0c-30aa124087a8',  # F1 2024 Season (sem vídeo)
]

def reprocess_bookmark(bookmark_id: str) -> bool:
    """
    Reprocessa um bookmark específico usando Celery task
    """
    logger.info(f"\n{'='*80}")

    # Buscar dados do bookmark
    response = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()

    if not response.data:
        logger.error(f"❌ Bookmark {bookmark_id} não encontrado")
        return False

    bookmark = response.data
    url = bookmark.get('original_url') or bookmark.get('url')
    title = bookmark.get('smart_title', 'Sem título')
    user_id = bookmark.get('user_id')

    logger.info(f"📹 Reprocessando: {title[:60]}...")
    logger.info(f"   ID: {bookmark_id}")
    logger.info(f"   URL: {url}")
    logger.info(f"   User ID: {user_id}")

    if not url:
        logger.error(f"❌ Bookmark não tem URL original")
        return False

    if not user_id:
        logger.error(f"❌ Bookmark não tem user_id")
        return False

    try:
        # Resetar status para pending
        supabase.table('bookmarks').update({
            'processing_status': 'pending',
            'ai_processed': False,
            'error_message': None
        }).eq('id', bookmark_id).execute()

        logger.info(f"   🔄 Disparando task Celery...")

        # Disparar task Celery (pipeline completo)
        task = process_bookmark_task.delay(
            bookmark_id=bookmark_id,
            url=url,
            user_id=user_id
        )

        logger.info(f"   ✅ Task disparada! Task ID: {task.id}")
        logger.info(f"   ⏳ O processamento vai rodar em background via Celery")
        logger.info(f"   📊 Acompanhe o status no banco: processing_status")

        return True

    except Exception as e:
        logger.error(f"   ❌ Erro ao disparar task: {str(e)}")
        return False

def main():
    logger.info("="*80)
    logger.info("🔧 Reprocessamento de 5 Bookmarks sem Thumbnail")
    logger.info(f"   Método: Celery pipeline completo (Apify + Gemini + Claude)")
    logger.info("="*80)

    success_count = 0
    fail_count = 0

    for i, bookmark_id in enumerate(bookmark_ids, 1):
        logger.info(f"\n[{i}/{len(bookmark_ids)}]")

        if reprocess_bookmark(bookmark_id):
            success_count += 1
        else:
            fail_count += 1

    logger.info("\n" + "="*80)
    logger.info(f"✅ TASKS DISPARADAS!")
    logger.info(f"   Sucesso: {success_count}")
    logger.info(f"   Falhas: {fail_count}")
    logger.info(f"\n   💡 O processamento está rodando em background via Celery")
    logger.info(f"   📊 Acompanhe o status checando processing_status no Supabase")
    logger.info("="*80)

if __name__ == "__main__":
    main()
