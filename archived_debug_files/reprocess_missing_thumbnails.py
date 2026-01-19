"""
Script para reprocessar bookmarks que estão sem thumbnail (cloud_thumbnail_url = NULL)
Usa o endpoint POST /bookmarks/{bookmark_id}/reprocess do backend
"""
import requests
import os
from supabase import create_client, Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

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

def reprocess_bookmark(bookmark_id: str) -> bool:
    """
    Reprocessa um bookmark específico chamando o endpoint do backend
    """
    # Buscar URL original do bookmark
    response = supabase.table('bookmarks').select('url, smart_title, original_url').eq('id', bookmark_id).single().execute()

    if not response.data:
        logger.error(f"❌ Bookmark {bookmark_id} não encontrado")
        return False

    bookmark = response.data
    url = bookmark.get('original_url') or bookmark.get('url')
    title = bookmark.get('smart_title', 'Sem título')

    if not url:
        logger.error(f"❌ Bookmark {bookmark_id} não tem URL")
        return False

    logger.info(f"\n📹 Reprocessando: {title[:60]}...")
    logger.info(f"   ID: {bookmark_id}")
    logger.info(f"   URL: {url}")

    try:
        # Chamar endpoint de reprocessamento
        endpoint = f"{BACKEND_URL}/bookmarks/{bookmark_id}/reprocess"
        logger.info(f"   🔄 Chamando: {endpoint}")

        response = requests.post(endpoint, timeout=300)  # 5 min timeout

        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Sucesso! Status: {data.get('status')}")
            return True
        else:
            logger.error(f"   ❌ Erro HTTP {response.status_code}: {response.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"   ❌ Timeout após 5 minutos")
        return False
    except Exception as e:
        logger.error(f"   ❌ Erro: {str(e)}")
        return False

def main():
    logger.info("="*80)
    logger.info("🔧 Reprocessamento de Bookmarks sem Thumbnail")
    logger.info(f"   Total: {len(bookmark_ids)} bookmarks")
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
    logger.info(f"✅ CONCLUÍDO!")
    logger.info(f"   Sucesso: {success_count}")
    logger.info(f"   Falhas: {fail_count}")
    logger.info("="*80)

if __name__ == "__main__":
    main()
