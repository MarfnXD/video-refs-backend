"""
PROCESSAMENTO EM BACKGROUND - FastAPI Background Tasks

Substitui Celery/Redis por sistema mais simples do FastAPI.
Processa bookmarks em background sem precisar de workers separados.

Funciona para até ~100 usuários, ~1000 vídeos/dia.
"""

import os
import logging
import asyncio
from typing import Optional
from supabase import create_client, Client
from services.apify_service import ApifyService
from services.claude_service import claude_service
from services.gemini_service import GeminiService
from services.video_storage_service import VideoStorageService
from services.thumbnail_service import ThumbnailService

logger = logging.getLogger(__name__)

# Supabase client (inicializar primeiro)
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Inicializar services
apify_service = ApifyService()
gemini_service = GeminiService()
video_storage_service = VideoStorageService()
thumbnail_service = ThumbnailService(supabase_client=supabase)


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
        apify_raw_response = None  # Resposta bruta do Apify para debug
        if extract_metadata:
            logger.info(f"📥 Extraindo metadados via Apify...")

            try:
                # Usa método unificado que detecta plataforma automaticamente
                video_metadata = await apify_service.extract_metadata(url)

                # Captura resposta bruta do Apify para debug
                apify_raw_response = apify_service.last_raw_response

                if video_metadata:
                    # Converter VideoMetadata para dict (campos corretos do modelo)
                    metadata = {
                        'title': video_metadata.title,
                        'description': video_metadata.description,
                        'thumbnail_url': video_metadata.thumbnail_url,
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

                    # Log se Apify retornou erro parcial
                    if apify_raw_response and apify_raw_response.get('error'):
                        logger.warning(f"⚠️ [{bookmark_id[:8]}] Apify retornou dados parciais: {apify_raw_response.get('error')}")
                else:
                    logger.warning(f"⚠️ Apify não retornou metadados")
                    apify_raw_response = apify_raw_response or {"fallback": True, "reason": "no_metadata"}
            except Exception as e:
                logger.error(f"❌ Erro ao extrair metadados: {str(e)}")
                apify_raw_response = {"fallback": True, "reason": "exception", "error": str(e)}
                # Não bloqueia - continua sem metadados

        # ============================================================
        # PASSO 3: Upload vídeo + Análise Gemini Flash 2.5
        # ============================================================
        gemini_analysis = None
        cloud_video_url = None
        temp_video_path = None

        if upload_to_cloud and metadata:
            try:
                # 3.1: Extrair URL direta do vídeo (Apify)
                logger.info(f"📥 Extraindo URL direta do vídeo...")

                # Detectar plataforma e extrair URL de download
                download_info = None
                if 'instagram' in url.lower():
                    download_info = await apify_service.extract_video_download_url_instagram(url)
                elif 'tiktok' in url.lower():
                    download_info = await apify_service.extract_video_download_url_tiktok(url)
                elif 'youtube' in url.lower() or 'youtu.be' in url.lower():
                    download_info = await apify_service.extract_video_download_url_youtube(url)

                if download_info and download_info.get('download_url'):
                    video_download_url = download_info['download_url']
                    logger.info(f"✅ URL direta obtida: {video_download_url[:50]}...")

                    # 3.2: Download + Upload para Supabase Storage
                    logger.info(f"☁️ Baixando e fazendo upload para Supabase Storage...")

                    upload_result = await video_storage_service.download_and_upload_video(
                        video_url=video_download_url,
                        user_id=user_id,
                        bookmark_id=bookmark_id
                    )

                    if upload_result:
                        cloud_video_url, temp_video_path = upload_result
                        logger.info(f"✅ Vídeo na cloud: {cloud_video_url[:50]}...")

                        # 3.3: Análise Gemini usando vídeo da cloud
                        if analyze_video:
                            logger.info(f"🎬 Analisando vídeo com Gemini Flash 2.5...")

                            try:
                                gemini_analysis = await gemini_service.analyze_video(
                                    video_url=cloud_video_url,
                                    user_context=user_context
                                )
                                logger.info(f"✅ Análise Gemini completa!")
                                logger.info(f"   Transcrição: {len(gemini_analysis.get('transcript', ''))} caracteres")
                                logger.info(f"   Análise Visual: {len(gemini_analysis.get('visual_analysis', ''))} caracteres")
                            except Exception as e:
                                logger.error(f"❌ Erro ao analisar com Gemini: {str(e)}")
                                # Gemini falhou mas vídeo já está na cloud (continua)
                    else:
                        logger.warning(f"⚠️ Upload para cloud falhou")
                else:
                    logger.warning(f"⚠️ Não foi possível extrair URL de download")

            except Exception as e:
                logger.error(f"❌ Erro no fluxo de upload/análise: {str(e)}")
                # Não bloqueia - continua sem vídeo na cloud

        # ============================================================
        # PASSO 4: Processar com IA (Claude)
        # ============================================================
        auto_description = None
        auto_tags = []
        auto_categories = []
        smart_title = None
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
                smart_title = result.get('smart_title')  # 🆕 Smart title já vem no JSON do Gemini!
                confidence = result.get('confidence')
                relevance_score = result.get('relevance_score')

                logger.info(f"✅ Claude processou: {len(auto_tags)} tags, {len(auto_categories)} categorias")
                if smart_title:
                    logger.info(f"✅ Smart title gerado: {smart_title[:60]}")
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

        # Salvar resposta bruta do Apify para debug (se existir)
        if apify_raw_response:
            update_data['apify_raw_response'] = apify_raw_response

        # Adicionar metadados se extraiu
        # IMPORTANTE: Só salvamos campos que EXISTEM na tabela bookmarks
        # Todos os outros dados estão no campo metadata (JSON)
        if metadata:
            update_data['title'] = metadata.get('title')
            update_data['original_title'] = metadata.get('title')  # Preserva título original
            update_data['platform'] = metadata.get('platform')
            update_data['thumbnail'] = metadata.get('thumbnail_url')  # URL original da thumbnail (Instagram)

            # Só adiciona published_at se tiver valor válido
            published_at = metadata.get('published_at')
            if published_at and published_at != '':
                update_data['published_at'] = published_at

            # 🔍 LOG CRÍTICO: Verificar metadata ANTES de salvar
            logger.info(f"🔍 [BACKGROUND_PROCESSOR] METADATA ANTES DE UPLOAD:")
            logger.info(f"   metadata['thumbnail_url']: {metadata.get('thumbnail_url', 'NULL')[:80] if metadata.get('thumbnail_url') else 'NULL'}...")
            logger.info(f"   metadata dict completo: {str(metadata)[:200]}...")

            # Upload da thumbnail para Supabase Storage (com retry automático)
            instagram_thumbnail_url = metadata.get('thumbnail_url')
            if instagram_thumbnail_url:
                try:
                    logger.info(f"📸 [{bookmark_id[:8]}] Upload thumbnail: {instagram_thumbnail_url[:60]}...")

                    cloud_thumbnail_url = await thumbnail_service.upload_thumbnail(
                        thumbnail_url=instagram_thumbnail_url,
                        user_id=user_id,
                        bookmark_id=bookmark_id
                    )

                    if cloud_thumbnail_url:
                        update_data['cloud_thumbnail_url'] = cloud_thumbnail_url
                        logger.info(f"✅ [{bookmark_id[:8]}] Thumbnail salva no Supabase Storage")
                    else:
                        # Retry final com delay maior (worker pode estar inicializando)
                        logger.warning(f"⚠️ [{bookmark_id[:8]}] Primeiro upload falhou, aguardando 5s para retry final...")
                        await asyncio.sleep(5)

                        try:
                            cloud_thumbnail_url = await thumbnail_service.upload_thumbnail(
                                thumbnail_url=instagram_thumbnail_url,
                                user_id=user_id,
                                bookmark_id=bookmark_id
                            )
                            if cloud_thumbnail_url:
                                update_data['cloud_thumbnail_url'] = cloud_thumbnail_url
                                logger.info(f"✅ [{bookmark_id[:8]}] Thumbnail salva no RETRY FINAL")
                            else:
                                # FALLBACK: Extrair frame do vídeo como thumbnail
                                if temp_video_path and os.path.exists(temp_video_path):
                                    logger.warning(f"🎬 [{bookmark_id[:8]}] Tentando fallback: extrair frame do vídeo...")
                                    cloud_thumbnail_url = await thumbnail_service.extract_frame_as_thumbnail(
                                        video_path=temp_video_path,
                                        user_id=user_id,
                                        bookmark_id=bookmark_id,
                                        timestamp_seconds=2.0  # Segundo 2 para evitar fades
                                    )
                                    if cloud_thumbnail_url:
                                        update_data['cloud_thumbnail_url'] = cloud_thumbnail_url
                                        logger.info(f"✅ [{bookmark_id[:8]}] Thumbnail via FRAME FALLBACK")
                                    else:
                                        logger.error(f"❌ [{bookmark_id[:8]}] Thumbnail falhou em TODAS as tentativas")
                                else:
                                    logger.error(f"❌ [{bookmark_id[:8]}] Sem vídeo local para fallback de frame")
                        except Exception as retry_error:
                            logger.error(f"❌ [{bookmark_id[:8]}] Erro no retry final: {str(retry_error)[:80]}")
                except Exception as e:
                    # Fallback de frame se tiver vídeo local
                    logger.error(f"❌ [{bookmark_id[:8]}] Erro no upload thumbnail: {str(e)[:80]}")
                    if temp_video_path and os.path.exists(temp_video_path):
                        logger.warning(f"🎬 [{bookmark_id[:8]}] Tentando fallback após exceção...")
                        try:
                            cloud_thumbnail_url = await thumbnail_service.extract_frame_as_thumbnail(
                                video_path=temp_video_path,
                                user_id=user_id,
                                bookmark_id=bookmark_id,
                                timestamp_seconds=2.0
                            )
                            if cloud_thumbnail_url:
                                update_data['cloud_thumbnail_url'] = cloud_thumbnail_url
                                logger.info(f"✅ [{bookmark_id[:8]}] Thumbnail via FRAME FALLBACK (após exceção)")
                        except Exception as fallback_error:
                            logger.error(f"❌ [{bookmark_id[:8]}] Fallback também falhou: {str(fallback_error)[:50]}")

            # 🔍 LOG CRÍTICO: Verificar metadata DEPOIS de upload
            logger.info(f"🔍 [BACKGROUND_PROCESSOR] METADATA DEPOIS DE UPLOAD:")
            logger.info(f"   metadata['thumbnail_url']: {metadata.get('thumbnail_url', 'NULL')[:80] if metadata.get('thumbnail_url') else 'NULL'}...")

            # AGORA adiciona metadata ao update_data (DEPOIS de logs)
            update_data['metadata'] = metadata  # JSON completo com TODOS os campos

            # 🔍 LOG CRÍTICO: Verificar o que vai ser salvo
            logger.info(f"💾 [BACKGROUND_PROCESSOR] DADOS QUE SERÃO SALVOS:")
            logger.info(f"   update_data['thumbnail']: {update_data.get('thumbnail', 'NULL')[:80] if update_data.get('thumbnail') else 'NULL'}...")
            logger.info(f"   update_data['cloud_thumbnail_url']: {update_data.get('cloud_thumbnail_url', 'NULL')[:80] if update_data.get('cloud_thumbnail_url') else 'NULL'}...")
            logger.info(f"   update_data['metadata']['thumbnail_url']: {update_data['metadata'].get('thumbnail_url', 'NULL')[:80] if update_data.get('metadata', {}).get('thumbnail_url') else 'NULL'}...")

        # Adicionar cloud_video_url se fez upload
        if cloud_video_url:
            update_data['cloud_video_url'] = cloud_video_url
            update_data['cloud_upload_status'] = 'completed'
            update_data['cloud_uploaded_at'] = 'now()'

        # Adicionar análise Gemini se rodou (SALVO SEPARADO - você vê o que Gemini "viu")
        if gemini_analysis:
            update_data['video_transcript'] = gemini_analysis.get('transcript')
            update_data['visual_analysis'] = gemini_analysis.get('visual_analysis')
            update_data['transcript_language'] = gemini_analysis.get('language')
            update_data['analyzed_at'] = 'now()'

        # Adicionar contexto do usuário (CRÍTICO - não pode perder!)
        if user_context:
            update_data['user_context_raw'] = user_context

        # Adicionar resultados da IA se processou
        if auto_description:
            update_data['auto_description'] = auto_description
            update_data['ai_processed'] = True  # Flag indicando processamento IA
        if auto_tags:
            update_data['auto_tags'] = auto_tags
        if auto_categories:
            update_data['auto_categories'] = auto_categories

        # Adicionar smart_title se foi gerado
        if smart_title:
            update_data['smart_title'] = smart_title

        # UPDATE no Supabase
        supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

        # Limpar arquivo temporário (libera espaço no Render)
        if temp_video_path:
            video_storage_service.cleanup_temp_file(temp_video_path)

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
