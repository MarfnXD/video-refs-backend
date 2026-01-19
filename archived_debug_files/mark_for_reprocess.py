"""
Script para marcar 5 bookmarks específicos para reprocessamento
Apenas reseta o status para 'pending' para que o Celery worker processe novamente
"""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client
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
    '7c91f5ca-910b-4eda-b2ad-828c2f5f4e6e',  # Travis Scott x Nike Ad (tem vídeo, falta thumb)
    'd35673ee-a112-48fe-9bf1-bafa3248d08d',  # Red Bull x Arcane (tem vídeo, falta thumb)
    '0223b7a0-8f46-4f16-b365-a7bbd5d6929d',  # App Instories (tem vídeo, falta thumb)
    '4a5d996b-4ac8-432c-b1f7-7beb1d3ee2ac',  # Sem título (SEM vídeo e SEM thumb)
    '2a6a9138-a57c-4c32-8a0c-30aa124087a8',  # F1 2024 (SEM vídeo e SEM thumb)
]

def mark_for_reprocess(bookmark_id: str) -> bool:
    """
    Marca bookmark para reprocessamento resetando status
    """
    # Buscar dados do bookmark
    response = supabase.table('bookmarks').select('smart_title, url, cloud_video_url').eq('id', bookmark_id).single().execute()

    if not response.data:
        logger.error(f"❌ [{bookmark_id[:8]}] Não encontrado")
        return False

    bookmark = response.data
    title = bookmark.get('smart_title') or 'Sem título'

    logger.info(f"\n📹 {title[:60] if title else 'Sem título'}...")
    logger.info(f"   ID: {bookmark_id}")

    # Resetar status
    update_data = {
        'processing_status': 'pending',
        'cloud_thumbnail_url': None,  # Forçar regerar thumbnail
        'ai_processed': False,
        'error_message': None
    }

    supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

    logger.info(f"   ✅ Marcado para reprocessamento (status=pending)")
    return True

def main():
    logger.info("="*80)
    logger.info("🔧 Marcando Bookmarks para Reprocessamento")
    logger.info(f"   Total: {len(bookmark_ids)} bookmarks")
    logger.info("="*80)

    success_count = 0

    for i, bookmark_id in enumerate(bookmark_ids, 1):
        logger.info(f"\n[{i}/{len(bookmark_ids)}]")

        if mark_for_reprocess(bookmark_id):
            success_count += 1

    logger.info("\n" + "="*80)
    logger.info(f"✅ CONCLUÍDO! {success_count} bookmarks marcados")
    logger.info(f"\n   💡 PRÓXIMO PASSO: Iniciar Celery worker para processar")
    logger.info(f"   📝 Comando: celery -A celery_app worker --loglevel=info")
    logger.info("="*80)

if __name__ == "__main__":
    main()
