"""
Script para debugar e reextrair metadados do bookmark "8-Bit Spill"
"""
import os
import asyncio
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega variáveis de ambiente do .env
load_dotenv()

from services.apify_service import ApifyService
from services.claude_service import claude_service
import logging

# Cria instância do ApifyService
apify_service = ApifyService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("SUPABASE_KEY ou SUPABASE_SERVICE_ROLE_KEY não configurada")

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

async def debug_and_reextract():
    """Debug e reextração de metadados do 8-Bit Spill"""

    bookmark_id = "419aa662-420c-4564-81c5-b2138def6b73"
    url = "https://www.instagram.com/reel/DPFquQ9DKc-/?igsh=eHhhYXhxbmdkdTBv"

    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 DEBUGANDO BOOKMARK: {bookmark_id}")
    logger.info(f"🔗 URL: {url}")

    # 1. Busca dados atuais no Supabase
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 ETAPA 1: DADOS ATUAIS NO SUPABASE")
    logger.info(f"{'='*80}")

    response = supabase.table('bookmarks') \
        .select('*') \
        .eq('id', bookmark_id) \
        .execute()

    if not response.data:
        logger.error(f"❌ Bookmark não encontrado!")
        return

    bookmark = response.data[0]
    metadata = bookmark.get('metadata', {}) or {}

    logger.info(f"\n📦 CAMPO METADATA:")
    logger.info(f"   Tipo: {type(metadata)}")
    logger.info(f"   Vazio? {len(metadata) == 0}")
    logger.info(f"   Chaves: {list(metadata.keys()) if metadata else 'NENHUMA'}")

    if metadata:
        logger.info(f"\n📝 CONTEÚDO DETALHADO:")
        for key, value in metadata.items():
            if isinstance(value, list):
                logger.info(f"   - {key}: [{len(value)} itens]")
                if len(value) > 0:
                    logger.info(f"     Primeiro item: {value[0]}")
            elif isinstance(value, str):
                preview = value[:100] + "..." if len(value) > 100 else value
                logger.info(f"   - {key}: {preview}")
            else:
                logger.info(f"   - {key}: {value}")

    logger.info(f"\n🤖 DADOS DE IA:")
    logger.info(f"   ai_processed: {bookmark.get('ai_processed', False)}")
    logger.info(f"   auto_description: {bookmark.get('auto_description', 'NENHUMA')[:100] if bookmark.get('auto_description') else 'NENHUMA'}")
    logger.info(f"   auto_tags: {bookmark.get('auto_tags', [])}")
    logger.info(f"   auto_categories: {bookmark.get('auto_categories', [])}")

    # 2. Tenta extrair metadados NOVAMENTE via Apify
    logger.info(f"\n{'='*80}")
    logger.info(f"📡 ETAPA 2: RE-EXTRAÇÃO VIA APIFY")
    logger.info(f"{'='*80}")

    try:
        logger.info(f"🔄 Chamando Apify para extrair metadados do Instagram...")
        new_metadata = await apify_service.extract_instagram_metadata(url)

        if new_metadata:
            logger.info(f"\n✅ NOVOS METADADOS EXTRAÍDOS:")
            logger.info(f"   Título: {new_metadata.get('title', 'N/A')}")
            logger.info(f"   Descrição: {new_metadata.get('description', 'N/A')[:100]}...")
            logger.info(f"   Hashtags: {len(new_metadata.get('hashtags', []))} tags")
            logger.info(f"   Comentários: {len(new_metadata.get('comments', []))} comentários")

            if new_metadata.get('comments'):
                logger.info(f"\n💬 PRIMEIROS 3 COMENTÁRIOS:")
                for i, comment in enumerate(new_metadata.get('comments', [])[:3], 1):
                    logger.info(f"   {i}. {comment.get('text', 'N/A')[:80]}...")

            # Salva novos metadados no Supabase
            logger.info(f"\n💾 Atualizando metadata no Supabase...")
            supabase.table('bookmarks').update({'metadata': new_metadata}).eq('id', bookmark_id).execute()
            logger.info(f"✅ Metadata atualizado!")

            # 3. Processa com IA usando os novos metadados
            logger.info(f"\n{'='*80}")
            logger.info(f"🤖 ETAPA 3: PROCESSAMENTO COM IA")
            logger.info(f"{'='*80}")

            result = await claude_service.process_metadata_auto(
                title=new_metadata.get('title', bookmark.get('title')),
                description=new_metadata.get('description', ''),
                hashtags=new_metadata.get('hashtags', []),
                top_comments=new_metadata.get('comments', []),
                video_transcript=bookmark.get('video_transcript', ''),
                visual_analysis=bookmark.get('visual_analysis', ''),
                user_context=bookmark.get('user_context_raw', '')
            )

            if result:
                # Salva resultados da IA
                update_data = {
                    'auto_description': result.get('auto_description'),
                    'auto_tags': result.get('auto_tags'),
                    'auto_categories': result.get('auto_categories'),
                    'relevance_score': result.get('relevance_score'),
                    'ai_processed': True
                }

                if 'filtered_comments' in result:
                    update_data['filtered_comments'] = result['filtered_comments']

                supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

                logger.info(f"\n✅ SUCESSO! DADOS DE IA SALVOS:")
                logger.info(f"   📝 auto_description: {result.get('auto_description')[:100]}...")
                logger.info(f"   🏷️ auto_tags: {result.get('auto_tags')}")
                logger.info(f"   📁 auto_categories: {result.get('auto_categories')}")
                logger.info(f"   ⭐ relevance_score: {result.get('relevance_score')}")
            else:
                logger.error(f"❌ Processamento de IA falhou")
        else:
            logger.error(f"❌ Apify não retornou metadados")

    except Exception as e:
        logger.error(f"❌ Erro na re-extração: {str(e)}")
        import traceback
        traceback.print_exc()

    logger.info(f"\n{'='*80}")
    logger.info(f"✅ DEBUG CONCLUÍDO!")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(debug_and_reextract())
