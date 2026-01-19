"""
Script para reprocessar as 10 referências mais recentes com o novo prompt otimizado
"""
import os
import asyncio
from supabase import create_client, Client
from services.claude_service import claude_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY não configurada")

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

async def reprocess_recent_10():
    """Reprocessa as 10 referências mais recentes"""

    # Busca as 10 mais recentes
    response = supabase.table('bookmarks') \
        .select('id, url, title, metadata, user_context_raw, video_transcript, visual_analysis, transcript_language') \
        .order('created_at', desc=True) \
        .limit(10) \
        .execute()

    bookmarks = response.data
    total = len(bookmarks)

    logger.info(f"📚 Encontradas {total} referências para reprocessar")

    for i, bookmark in enumerate(bookmarks, 1):
        bookmark_id = bookmark['id']
        title = bookmark.get('title', 'Sem título')

        logger.info(f"\n{'='*80}")
        logger.info(f"[{i}/{total}] 🔄 Reprocessando: {title[:60]}...")
        logger.info(f"ID: {bookmark_id}")

        try:
            # Extrai dados do metadata
            metadata = bookmark.get('metadata', {}) or {}
            description = metadata.get('description', '')
            hashtags = metadata.get('hashtags', [])
            comments = metadata.get('comments', [])

            # Contexto do usuário (se houver)
            user_context = bookmark.get('user_context_raw', '') or ''

            # Análise multimodal
            video_transcript = bookmark.get('video_transcript', '') or ''
            visual_analysis = bookmark.get('visual_analysis', '') or ''

            # Log dos dados
            logger.info(f"  📝 Contexto do usuário: {'✅ Sim' if user_context else '❌ Não'}")
            logger.info(f"  🎤 Transcrição: {'✅ Sim' if video_transcript else '❌ Não'}")
            logger.info(f"  🖼️ Análise visual: {'✅ Sim' if visual_analysis else '❌ Não'}")
            logger.info(f"  💬 Comentários: {len(comments)} total")

            # Processa com Claude (novo prompt otimizado)
            result = await claude_service.process_metadata_auto(
                title=title,
                description=description,
                hashtags=hashtags,
                top_comments=comments,
                video_transcript=video_transcript,
                visual_analysis=visual_analysis,
                user_context=user_context  # ← NOVO PARÂMETRO!
            )

            if result:
                # Salva no Supabase
                update_data = {
                    'auto_description': result.get('auto_description'),
                    'auto_tags': result.get('auto_tags'),
                    'auto_categories': result.get('auto_categories'),
                    'relevance_score': result.get('relevance_score'),
                    'ai_processed': True
                }

                # Comentários filtrados (se houver)
                if 'filtered_comments' in result:
                    update_data['filtered_comments'] = result['filtered_comments']
                    logger.info(f"  ✅ {len(result['filtered_comments'])} comentários filtrados salvos")

                supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

                logger.info(f"  ✅ auto_description: {result.get('auto_description')[:80]}...")
                logger.info(f"  ✅ auto_tags: {result.get('auto_tags')}")
                logger.info(f"  ✅ auto_categories: {result.get('auto_categories')}")
                logger.info(f"  ✅ confidence: {result.get('confidence')}")
                logger.info(f"  ✅ Salvo no Supabase!")
            else:
                logger.error(f"  ❌ Processamento falhou (sem resultado)")

        except Exception as e:
            logger.error(f"  ❌ Erro ao processar bookmark {bookmark_id}: {str(e)}")
            continue

    logger.info(f"\n{'='*80}")
    logger.info(f"✅ CONCLUÍDO! {total} referências reprocessadas")

if __name__ == "__main__":
    asyncio.run(reprocess_recent_10())
