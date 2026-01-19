"""
Script para disparar tasks Celery para os 5 bookmarks marcados para reprocessamento
"""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client
from tasks import process_bookmark_complete_task
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
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
    '7c91f5ca-910b-4eda-b2ad-828c2f5f4e6e',
    'd35673ee-a112-48fe-9bf1-bafa3248d08d',
    '0223b7a0-8f46-4f16-b365-a7bbd5d6929d',
    '4a5d996b-4ac8-432c-b1f7-7beb1d3ee2ac',
    '2a6a9138-a57c-4c32-8a0c-30aa124087a8'
]

def dispatch_task(bookmark_id: str) -> bool:
    """
    Dispara task Celery para reprocessar bookmark
    """
    # Buscar dados do bookmark
    response = supabase.table('bookmarks').select('url, user_id, smart_title').eq('id', bookmark_id).single().execute()

    if not response.data:
        logger.error(f"❌ [{bookmark_id[:8]}] Não encontrado")
        return False

    bookmark = response.data
    url = bookmark.get('url')
    user_id = bookmark.get('user_id')
    title = bookmark.get('smart_title') or 'Sem título'

    if not url:
        logger.error(f"❌ [{bookmark_id[:8]}] Sem URL")
        return False

    if not user_id:
        logger.error(f"❌ [{bookmark_id[:8]}] Sem user_id")
        return False

    logger.info(f"\n📹 {title[:60] if title else 'Sem título'}...")
    logger.info(f"   ID: {bookmark_id[:8]}...")
    logger.info(f"   URL: {url}")

    try:
        # Disparar task Celery
        task = process_bookmark_complete_task.delay(
            bookmark_id=bookmark_id,
            url=url,
            user_id=user_id
        )

        logger.info(f"   ✅ Task disparada! Task ID: {task.id}")
        return True

    except Exception as e:
        logger.error(f"   ❌ Erro: {str(e)}")
        return False

def main():
    logger.info("="*80)
    logger.info("🚀 Disparando Tasks Celery para Reprocessamento")
    logger.info(f"   Total: {len(bookmark_ids)} bookmarks")
    logger.info("="*80)

    success_count = 0

    for i, bookmark_id in enumerate(bookmark_ids, 1):
        logger.info(f"\n[{i}/{len(bookmark_ids)}]")

        if dispatch_task(bookmark_id):
            success_count += 1

    logger.info("\n" + "="*80)
    logger.info(f"✅ {success_count} tasks disparadas com sucesso!")
    logger.info(f"\n   💡 Acompanhe o processamento no log do Celery worker")
    logger.info("="*80)

if __name__ == "__main__":
    main()
