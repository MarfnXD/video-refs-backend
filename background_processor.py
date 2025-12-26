"""
PROCESSAMENTO EM BACKGROUND - FastAPI Background Tasks

Substitui Celery/Redis por sistema mais simples do FastAPI.
Processa bookmarks em background sem precisar de workers separados.

Funciona para até ~100 usuários, ~1000 vídeos/dia.
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client
from services.apify_service import ApifyService
from services.claude_service import claude_service
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# Inicializar services
apify_service = ApifyService()
gemini_service = GeminiService()

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)


async def process_bookmark_background(
    bookmark_id: str,
    url: str,
    user_id: str,
    extract_metadata: bool = True,
    analyze_video: bool = True,
    process_ai: bool = True,
    upload_to_cloud: bool = False,
    user_context: Optional[str] = None
):
    """
    Processa bookmark completo em background.

    Fluxo:
    1. Atualiza status: processing
    2. Extrai metadados (Apify)
    3. Analisa vídeo (Gemini Flash 2.5) - OPCIONAL
    4. Processa com IA (Claude)
    5. Atualiza Supabase com tudo
    6. Status final: completed ou failed
    """
    try:
        logger.info(f"🚀 INICIANDO processamento - Bookmark: {bookmark_id}")

        # ============================================================
        # PASSO 1: Atualizar status → processing
        # ============================================================
        supabase.table('bookmarks').update({
            'processing_status': 'processing',
            'processing_started_at': 'now()',
            'error_message': None
        }).eq('id', bookmark_id).execute()

        logger.info(f"✅ Status atualizado: processing")

        # ============================================================
        # PASSO 2: Extrair metadados (Apify)
        # ============================================================
        metadata = None
        if extract_metadata:
            logger.info(f"📥 Extraindo metadados via Apify...")

            try:
                # Usa método unificado que detecta plataforma automaticamente
                video_metadata = await apify_service.extract_metadata(url)

                if video_metadata:
                    # Converter VideoMetadata para dict (campos corretos do modelo)
                    metadata = {
                        'title': video_metadata.title,
                        'description': video_metadata.description,
                        'thumbnail_url': video_metadata.thumbnail_url,
                        'cloud_thumbnail_url': video_metadata.cloud_thumbnail_url,
                        'duration': video_metadata.duration,
                        'views': video_metadata.views,
                        'likes': video_metadata.likes,
                        'comments_count': video_metadata.comments_count,
                        'author': video_metadata.author,
                        'author_url': video_metadata.author_url,
                        'published_at': video_metadata.published_at,
                        'hashtags': video_metadata.hashtags,
                        'top_comments': [
                            {'text': c.text, 'author': c.author, 'likes': c.likes}
                            for c in video_metadata.top_comments
                        ] if video_metadata.top_comments else [],
                        'platform': video_metadata.platform.value if video_metadata.platform else None,
                    }
                    logger.info(f"✅ Metadados extraídos: {metadata.get('title', 'N/A')[:50]}")
                else:
                    logger.warning(f"⚠️ Apify não retornou metadados")
            except Exception as e:
                logger.error(f"❌ Erro ao extrair metadados: {str(e)}")
                # Não bloqueia - continua sem metadados

        # ============================================================
        # PASSO 3: Analisar vídeo com Gemini Flash 2.5 (OPCIONAL)
        # ============================================================
        # DESABILITADO TEMPORARIAMENTE - VideoMetadata não tem direct_video_url
        # TODO: Integrar com serviço de download para obter URL direta
        gemini_analysis = None
        # if analyze_video and metadata:
        #     logger.info(f"🎬 Analisando vídeo com Gemini Flash 2.5...")
        #     try:
        #         gemini_analysis = await gemini_service.analyze_video(
        #             video_url=url,
        #             user_context=user_context
        #         )
        #         logger.info(f"✅ Análise Gemini completa!")
        #     except Exception as e:
        #         logger.error(f"❌ Erro ao analisar com Gemini: {str(e)}")

        # ============================================================
        # PASSO 4: Processar com IA (Claude)
        # ============================================================
        auto_description = None
        auto_tags = []
        auto_categories = []
        confidence = None
        relevance_score = None

        if process_ai and metadata:
            logger.info(f"🤖 Processando com Claude API...")

            try:
                # Se tem análise Gemini, usa método com Gemini
                if gemini_analysis:
                    result = await claude_service.process_metadata_with_gemini(
                        title=metadata.get('title', ''),
                        description=metadata.get('description', ''),
                        hashtags=metadata.get('hashtags', []),
                        top_comments=metadata.get('top_comments', []),
                        gemini_analysis=gemini_analysis,
                        user_context=user_context
                    )
                else:
                    # Método tradicional (sem Gemini)
                    result = await claude_service.process_metadata_auto(
                        title=metadata.get('title', ''),
                        description=metadata.get('description', ''),
                        hashtags=metadata.get('hashtags', []),
                        top_comments=metadata.get('top_comments', []),
                        user_context=user_context
                    )

                auto_description = result.get('auto_description')
                auto_tags = result.get('auto_tags', [])
                auto_categories = result.get('auto_categories', [])
                confidence = result.get('confidence')
                relevance_score = result.get('relevance_score')

                logger.info(f"✅ Claude processou: {len(auto_tags)} tags, {len(auto_categories)} categorias")
            except Exception as e:
                logger.error(f"❌ Erro ao processar com Claude: {str(e)}")
                # Não bloqueia - continua sem IA

        # ============================================================
        # PASSO 5: Atualizar Supabase com TUDO
        # ============================================================
        logger.info(f"💾 Salvando tudo no Supabase...")

        update_data = {
            'processing_status': 'completed',
            'processing_completed_at': 'now()',
            'error_message': None
        }

        # Adicionar metadados se extraiu
        # IMPORTANTE: Só salvamos campos que EXISTEM na tabela bookmarks
        # Todos os outros dados estão no campo metadata (JSON)
        if metadata:
            update_data['title'] = metadata.get('title')
            update_data['platform'] = metadata.get('platform')
            update_data['metadata'] = metadata  # JSON completo com TODOS os campos

        # Adicionar análise Gemini se rodou
        if gemini_analysis:
            update_data['video_transcript'] = gemini_analysis.get('transcript')
            update_data['visual_analysis'] = gemini_analysis.get('visual_analysis')
            update_data['transcript_language'] = gemini_analysis.get('language')
            update_data['analyzed_at'] = 'now()'

        # Adicionar resultados da IA se processou
        if auto_description:
            update_data['auto_description'] = auto_description
        if auto_tags:
            update_data['auto_tags'] = auto_tags
        if auto_categories:
            update_data['auto_categories'] = auto_categories

        # UPDATE no Supabase
        supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

        logger.info(f"✅ PROCESSAMENTO COMPLETO - Bookmark: {bookmark_id}")
        logger.info(f"   Status: completed")
        logger.info(f"   Metadados: {'✅' if metadata else '❌'}")
        logger.info(f"   Gemini: {'✅' if gemini_analysis else '❌'}")
        logger.info(f"   Claude: {'✅' if auto_description else '❌'}")

    except Exception as e:
        logger.error(f"❌ ERRO no processamento - Bookmark: {bookmark_id}")
        logger.error(f"   Erro: {str(e)}", exc_info=True)

        # Atualizar status: failed
        try:
            supabase.table('bookmarks').update({
                'processing_status': 'failed',
                'processing_completed_at': 'now()',
                'error_message': str(e)[:500]  # Limita tamanho do erro
            }).eq('id', bookmark_id).execute()
        except Exception as update_error:
            logger.error(f"❌ Erro ao atualizar status failed: {str(update_error)}")
