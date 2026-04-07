"""
Celery Tasks - Background Jobs
Tasks assíncronas processadas pelos workers
"""
from celery_app import celery_app
from celery import chain, group
from typing import Optional, List, Dict
import logging
import os
import tempfile
from datetime import datetime
import asyncio
import time
from dotenv import load_dotenv

# Carregar env vars
load_dotenv()

# Services
from services.apify_service import ApifyService
from services.gemini_service import gemini_service
from services.claude_service import claude_service
from services.thumbnail_service import ThumbnailService
from services.embedding_service import embedding_service
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER: Logging com timing
# ============================================================================

class TaskTimer:
    """Helper para medir duração de tasks e criar logs consolidados"""

    def __init__(self, task_name: str, bookmark_id: str):
        self.task_name = task_name
        self.bookmark_id = bookmark_id
        self.start_time = None

    def start(self):
        """Inicia timer e loga início da task"""
        self.start_time = time.time()
        logger.info(f"📊 [{self.task_name}] {self.bookmark_id} - INÍCIO")

    def success(self, **details):
        """Loga sucesso com duração e detalhes"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
        logger.info(
            f"✅ [{self.task_name}] {self.bookmark_id} - SUCESSO | "
            f"{details_str} | {elapsed:.1f}s"
        )

    def error(self, error_msg: str):
        """Loga erro com duração"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.error(
            f"❌ [{self.task_name}] {self.bookmark_id} - ERRO | "
            f"{error_msg} | {elapsed:.1f}s"
        )

# Inicializar services
apify_service = ApifyService()

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase_client: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
thumbnail_service = ThumbnailService(supabase_client) if supabase_client else None


# ============================================================================
# TASK PRINCIPAL: Processar bookmark completo
# ============================================================================

@celery_app.task(bind=True, name="tasks.process_bookmark_complete_task")
def process_bookmark_complete_task(
    self,
    bookmark_id: str,
    url: str,
    user_id: str,
    extract_metadata: bool = True,
    analyze_video: bool = True,
    process_ai: bool = True,
    upload_to_cloud: bool = False
):
    """
    Task principal que orquestra TODO o processamento de um bookmark.

    Executa em cadeia (chain):
    1. Extrai metadados (Apify)
    2. Upload pra cloud (se upload_to_cloud=True) - ANTES da análise!
    3. Analisa vídeo com Gemini 2.5 Flash (usa cloud_video_url)
    4. Processa com Gemini 3.0 Pro (tags, categorias, descrição)
    5. Cleanup e notificação

    Args:
        bookmark_id: UUID do bookmark no Supabase
        url: URL do vídeo (YouTube/Instagram/TikTok)
        user_id: UUID do usuário
        extract_metadata: Extrair metadados (título, descrição, etc)
        analyze_video: Analisar vídeo com Gemini 2.5 Flash (áudio + visual)
        process_ai: Processar com Gemini 3.0 Pro (tags/categorias)
        upload_to_cloud: Fazer upload do vídeo pra Supabase Storage

    Returns:
        dict: Resultado final do processamento
    """
    # Extrair domínio da URL para log
    url_domain = url.split('/')[2] if '/' in url else url[:30]
    logger.info(f"🚀 [PIPELINE] {bookmark_id} - INÍCIO | URL: {url_domain}")

    # Atualizar status no Supabase: queued → processing
    update_bookmark_status(bookmark_id, "processing", self.request.id)

    try:
        # Criar pipeline de tasks (executam em sequência)
        # IMPORTANTE: Tasks encadeadas recebem resultado da anterior via primeiro parâmetro
        # Formato: task.s() = signature imutável (parâmetros fixos)
        #          task.signature() ou task.si() = signature imutável completa

        # 1. Extração de metadados (sempre roda primeiro)
        if extract_metadata:
            # Primeira task: passa parâmetros explícitos
            workflow = extract_metadata_task.s(bookmark_id, url, user_id)

            # 2. Upload pra cloud (ANTES da análise - URLs do Instagram expiram rápido!)
            if upload_to_cloud:
                workflow |= upload_to_cloud_task.s(bookmark_id, user_id)

            # 3. Análise com Gemini (usa cloud_video_url se disponível)
            if analyze_video:
                # Gemini precisa dos dados da task anterior + bookmark_id + url
                # .s() cria signature parcial - primeiro arg vem da task anterior
                workflow |= analyze_video_gemini_task.s(bookmark_id, url)

            # 4. Processamento Gemini 3.0 Pro (recebe resultado anterior)
            if process_ai:
                workflow |= process_claude_task.s(bookmark_id, user_id)

            # 5. Gerar embedding (sempre roda após processamento IA)
            if process_ai:
                workflow |= generate_embedding_task.s(bookmark_id, user_id)

            # 6. Cleanup final (sempre roda)
            workflow |= cleanup_and_notify_task.s(bookmark_id, user_id)

            # Executar workflow
            result = workflow.apply_async()

        else:
            # Se não extrair metadados, só roda cleanup
            result = cleanup_and_notify_task.si(
                {"bookmark_id": bookmark_id, "message": "Nenhum processamento solicitado"},
                bookmark_id,
                user_id
            ).apply_async()

        # Log estruturado do pipeline (ordem de execução)
        pipeline_config = []
        if extract_metadata:
            pipeline_config.append("Metadata:✓")
        if upload_to_cloud:
            pipeline_config.append("Upload:✓")
        if analyze_video:
            pipeline_config.append("Gemini:✓")
        if process_ai:
            pipeline_config.append("Gemini Pro:✓")
            pipeline_config.append("Embedding:✓")

        logger.info(
            f"✅ [PIPELINE] {bookmark_id} - CRIADO | "
            f"{' '.join(pipeline_config)} | Job: {self.request.id[:8]}"
        )

        return {
            "success": True,
            "bookmark_id": bookmark_id,
            "job_id": self.request.id,
            "pipeline_id": result.id
        }

    except Exception as e:
        logger.error(f"❌ [PIPELINE] {bookmark_id} - ERRO | {str(e)[:100]}")
        update_bookmark_status(bookmark_id, "failed", self.request.id, str(e))
        raise


# ============================================================================
# TASKS INDIVIDUAIS (implementação nas próximas fases)
# ============================================================================

@celery_app.task(bind=True, name="tasks.extract_metadata_task", max_retries=3)
def extract_metadata_task(self, bookmark_id: str, url: str, user_id: str):
    """
    FASE 3.1: Extrair metadados com Apify
    - Scraping YouTube/Instagram/TikTok
    - Upload de thumbnail pra Supabase Storage
    - Salvar metadados no database
    """
    timer = TaskTimer("METADATA", bookmark_id)
    timer.start()

    try:
        # 1. Extrair metadados com Apify
        logger.debug(f"Chamando Apify para URL: {url[:60]}")
        loop = asyncio.get_event_loop()
        metadata = loop.run_until_complete(apify_service.extract_metadata(url))

        if not metadata:
            raise Exception("Apify retornou None - falha na extração de metadados")

        # 2. Upload de thumbnail pra Supabase Storage
        cloud_thumbnail_url = None
        if metadata.thumbnail_url and thumbnail_service:
            try:
                logger.info(f"📸 [TASKS.PY] Chamando ThumbnailService.upload_thumbnail()")
                logger.info(f"   - thumbnail_url (Instagram CDN): {metadata.thumbnail_url[:80]}...")
                logger.info(f"   - user_id: {user_id}")
                logger.info(f"   - bookmark_id: {bookmark_id}")

                cloud_thumbnail_url = loop.run_until_complete(
                    thumbnail_service.upload_thumbnail(
                        metadata.thumbnail_url,
                        user_id,
                        bookmark_id
                    )
                )

                if cloud_thumbnail_url:
                    logger.info(f"✅ [TASKS.PY] Upload OK → cloud_thumbnail_url: {cloud_thumbnail_url[:80]}...")
                else:
                    logger.warning(f"⚠️ [TASKS.PY] Upload retornou None")
            except Exception as e:
                logger.warning(f"⚠️ Thumbnail upload falhou (não crítico): {str(e)[:50]}")

        # 3. Salvar metadados no Supabase
        metadata_dict = metadata.dict()

        # 🔍 LOG CRÍTICO: Verificar se metadata.thumbnail_url está correto
        logger.info(f"🔍 [TASKS.PY] ANTES DE SALVAR:")
        logger.info(f"   metadata.thumbnail_url (objeto): {metadata.thumbnail_url[:80] if metadata.thumbnail_url else 'NULL'}...")
        logger.info(f"   metadata.dict()['thumbnail_url']: {metadata_dict.get('thumbnail_url', 'NULL')[:80] if metadata_dict.get('thumbnail_url') else 'NULL'}...")
        logger.info(f"   cloud_thumbnail_url: {cloud_thumbnail_url[:80] if cloud_thumbnail_url else 'NULL'}...")

        update_data = {
            'title': metadata.title,
            'original_title': metadata.title,  # Imutável
            'platform': metadata.platform.value if hasattr(metadata.platform, 'value') else str(metadata.platform),
            'thumbnail_url': metadata.thumbnail_url,
            'metadata': metadata_dict,  # JSON completo (Pydantic v1)
        }

        # Adicionar cloud_thumbnail_url se disponível
        if cloud_thumbnail_url:
            update_data['cloud_thumbnail_url'] = cloud_thumbnail_url

        # Adicionar published_at se disponível
        if metadata.published_at:
            update_data['published_at'] = metadata.published_at

        # Update no database
        supabase_client.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

        # 🔍 LOG CRÍTICO: Verificar o que foi salvo
        logger.info(f"💾 [TASKS.PY] SALVO NO BANCO:")
        logger.info(f"   update_data['metadata']['thumbnail_url']: {update_data['metadata'].get('thumbnail_url', 'NULL')[:80] if update_data['metadata'].get('thumbnail_url') else 'NULL'}...")

        # Log consolidado de sucesso
        timer.success(
            Título=metadata.title[:30] if metadata.title else "N/A",
            Thumb="✓" if cloud_thumbnail_url else "✗",
            Platform=update_data['platform']
        )

        # 4. Extrair video_download_url do raw response (evita 2a chamada Apify)
        video_download_url = None
        raw = apify_service.last_raw_response
        if raw and isinstance(raw, dict):
            # TikTok: video.downloadAddr
            if raw.get("video"):
                video_download_url = raw["video"].get("downloadAddr") or raw["video"].get("playAddr")
            # Instagram: videoUrl
            elif raw.get("videoUrl"):
                video_download_url = raw["videoUrl"]

        # 5. Retornar dados para próxima task
        return {
            "bookmark_id": bookmark_id,
            "url": url,
            "user_id": user_id,
            "metadata_extracted": True,
            "title": metadata.title,
            "description": metadata.description or "",
            "hashtags": [tag.strip('#') for tag in (metadata.hashtags or [])],
            "top_comments": [
                {
                    "text": c.text,
                    "likes": c.likes,
                    "author": c.author
                } for c in (metadata.comments or [])[:200]  # Top 200 comments
            ],
            "cloud_thumbnail_url": cloud_thumbnail_url,
            "platform": update_data['platform'],
            "video_download_url": video_download_url,
        }

    except Exception as e:
        timer.error(f"Apify: {str(e)[:60]}")

        # Atualizar status no Supabase
        update_bookmark_status(bookmark_id, "failed", self.request.id, f"Erro na extração de metadados: {str(e)}")

        # Retry se for erro temporário
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            logger.warning(f"⚠️ Retry após 30s (timeout/connection)")
            raise self.retry(exc=e, countdown=30)  # Retry após 30s

        raise


@celery_app.task(bind=True, name="tasks.analyze_video_gemini_task", max_retries=2, time_limit=600)
def analyze_video_gemini_task(self, previous_result: dict, bookmark_id: str, url: str):
    """
    FASE 3.2: Analisar vídeo com Gemini Flash 2.5
    - Download temporário do vídeo (ou usa cloud_video_url se disponível)
    - Análise multimodal (áudio + visual + movimento)
    - Salvar transcrição e análise visual no database
    """
    timer = TaskTimer("GEMINI", bookmark_id)
    timer.start()

    temp_video_path = None

    try:
        # 1. Obter URL do vídeo para análise
        video_url_for_analysis = None
        user_context = previous_result.get('user_context', '')

        # Verificar se já tem vídeo na cloud
        if 'cloud_video_url' in previous_result and previous_result['cloud_video_url']:
            video_url_for_analysis = previous_result['cloud_video_url']
            logger.debug(f"Usando vídeo da cloud: {video_url_for_analysis[:60]}")
        elif previous_result.get('video_download_url'):
            # Reusa URL extraída na task anterior (evita 2a chamada Apify)
            video_url_for_analysis = previous_result['video_download_url']
            logger.info(f"♻️ Reusando video_download_url do pipeline (sem chamada extra Apify)")
        else:
            # Fallback: Baixar vídeo via Apify (só se pipeline não passou a URL)
            logger.debug("Baixando vídeo temporário via Apify (fallback)")
            loop = asyncio.get_event_loop()

            from models import Platform
            platform = apify_service.detect_platform(url)

            if platform == Platform.YOUTUBE:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_youtube(url, quality="720p")
                )
            elif platform == Platform.INSTAGRAM:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_instagram(url, quality="720p")
                )
            elif platform == Platform.TIKTOK:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_tiktok(url, quality="720p")
                )
            elif platform == Platform.X:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_x(url, quality="720p")
                )
            else:
                raise Exception(f"Plataforma não suportada: {platform}")

            if not video_data or not video_data.get('download_url'):
                raise Exception("Falha ao extrair URL do vídeo")

            video_url_for_analysis = video_data['download_url']

        # 2. Analisar vídeo com Gemini Flash 2.5
        loop = asyncio.get_event_loop()
        gemini_analysis = loop.run_until_complete(
            gemini_service.analyze_video(video_url_for_analysis, user_context)
        )

        if not gemini_analysis:
            raise Exception("Gemini retornou None")

        # 3. Salvar análise no Supabase
        update_data = {
            'video_transcript': gemini_analysis.get('transcript', ''),
            'visual_analysis': gemini_analysis.get('visual_analysis', ''),
            'transcript_language': gemini_analysis.get('language', 'unknown'),
            'analyzed_at': datetime.utcnow().isoformat(),
        }

        supabase_client.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

        # Log consolidado de sucesso
        timer.success(
            Idioma=gemini_analysis.get('language', 'N/A'),
            FOOH="Sim" if gemini_analysis.get('is_fooh') else "Não",
            Transcript=f"{len(gemini_analysis.get('transcript', ''))} chars"
        )

        # 4. Retornar dados para próxima task
        return {
            **previous_result,
            "video_analyzed": True,
            "gemini_analysis": gemini_analysis,
            "transcript": gemini_analysis.get('transcript', ''),
            "visual_analysis": gemini_analysis.get('visual_analysis', ''),
            "editing_techniques": gemini_analysis.get('editing_techniques', []),
            "is_fooh": gemini_analysis.get('is_fooh', False),
            "language": gemini_analysis.get('language', 'unknown')
        }

    except Exception as e:
        timer.error(f"Gemini: {str(e)[:60]}")

        # Atualizar status no Supabase
        update_bookmark_status(bookmark_id, "failed", self.request.id, f"Erro na análise Gemini: {str(e)}")

        # Retry se for erro temporário
        if "timeout" in str(e).lower() or "rate limit" in str(e).lower():
            logger.warning(f"⚠️ Retry após 60s (timeout/rate limit)")
            raise self.retry(exc=e, countdown=60)  # Retry após 60s

        raise

    finally:
        # Cleanup: deletar vídeo temporário se foi criado
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.unlink(temp_video_path)
                logger.debug(f"Vídeo temporário deletado: {temp_video_path}")
            except:
                pass


@celery_app.task(bind=True, name="tasks.process_claude_task", max_retries=2, time_limit=300)
def process_claude_task(self, previous_result: dict, bookmark_id: str, user_id: str):
    """
    FASE 3.3: Processar com Gemini 3.0 Pro
    - Juntar metadados + análise Gemini 2.5 Flash + contexto do usuário
    - Gerar tags, categorias, descrição automática
    - Salvar no database
    """
    timer = TaskTimer("GEMINI_PRO", bookmark_id)
    timer.start()

    try:
        # 1. Extrair dados do previous_result
        title = previous_result.get('title', '')
        description = previous_result.get('description', '')
        hashtags = previous_result.get('hashtags', [])
        top_comments = previous_result.get('top_comments', [])
        gemini_analysis = previous_result.get('gemini_analysis', None)
        user_context = previous_result.get('user_context', '')

        if not title:
            raise Exception("Título não disponível")

        logger.debug(f"Dados: título={title[:30]}, Gemini={'✓' if gemini_analysis else '✗'}, user_context={'✓' if user_context else '✗'}")

        # 2. Chamar Gemini 3.0 Pro
        loop = asyncio.get_event_loop()

        # Se tem análise Gemini, usar novo método
        if gemini_analysis:
            result = loop.run_until_complete(
                claude_service.process_metadata_with_gemini(
                    title=title,
                    description=description,
                    hashtags=hashtags,
                    top_comments=top_comments,
                    gemini_analysis=gemini_analysis,
                    user_context=user_context
                )
            )
        else:
            # Fallback: usar método antigo (sem análise de vídeo)
            logger.warning("⚠️ Sem análise Gemini - usando fallback")
            result = loop.run_until_complete(
                claude_service.process_metadata_auto(
                    title=title,
                    description=description,
                    hashtags=hashtags,
                    top_comments=top_comments,
                    user_context=user_context
                )
            )

        if not result:
            raise Exception("Gemini Pro retornou None")

        # 3. Gerar Smart Title (título otimizado para recuperação - metodologia CODE)
        smart_title = None
        try:
            logger.debug("🏷️ Gerando smart title...")

            # Extrair visual_analysis se disponível
            visual_analysis = previous_result.get('visual_analysis', None)

            smart_title = loop.run_until_complete(
                claude_service.generate_smart_title(
                    auto_description=result.get('auto_description', ''),
                    auto_tags=result.get('auto_tags', []),
                    user_context=user_context,
                    visual_analysis=visual_analysis
                )
            )

            if smart_title:
                logger.info(f"✅ Smart title gerado: {smart_title[:60]}")
            else:
                logger.warning("⚠️ Smart title retornou None - usando título original")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gerar smart title (não crítico): {str(e)[:50]}")
            smart_title = None

        # 4. Salvar no Supabase

        update_data = {
            'auto_description': result.get('auto_description', ''),
            'auto_tags': result.get('auto_tags', []),
            'auto_categories': result.get('auto_categories', []),
            'relevance_score': result.get('relevance_score', 0.5),
            'ai_processed': True,
        }

        # Adicionar smart_title se foi gerado
        if smart_title:
            update_data['smart_title'] = smart_title

        # Adicionar filtered_comments se disponível
        if 'filtered_comments' in result:
            # Extrair apenas campos necessários (economizar espaço no DB)
            filtered_comments_simple = [
                {
                    'text': c.get('text', ''),
                    'likes': c.get('likes', 0)
                }
                for c in result['filtered_comments'][:50]  # Top 50
            ]
            update_data['filtered_comments'] = filtered_comments_simple

        supabase_client.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

        # Log consolidado de sucesso
        timer.success(
            Tags=len(result.get('auto_tags', [])),
            Categorias=len(result.get('auto_categories', [])),
            Relevância=f"{result.get('relevance_score', 0):.2f}",
            SmartTitle="✓" if smart_title else "✗"
        )

        # 4. Retornar dados para próxima task
        return {
            **previous_result,
            "ai_processed": True,
            "auto_description": result.get('auto_description', ''),
            "auto_tags": result.get('auto_tags', []),
            "auto_categories": result.get('auto_categories', []),
            "relevance_score": result.get('relevance_score', 0.5),
        }

    except Exception as e:
        timer.error(f"Gemini Pro: {str(e)[:60]}")

        # Atualizar status no Supabase
        update_bookmark_status(bookmark_id, "failed", self.request.id, f"Erro no processamento Gemini Pro: {str(e)}")

        # Retry se for erro temporário
        if "timeout" in str(e).lower() or "rate limit" in str(e).lower():
            logger.warning(f"⚠️ Retry após 45s (timeout/rate limit)")
            raise self.retry(exc=e, countdown=45)  # Retry após 45s

        raise


@celery_app.task(bind=True, name="tasks.upload_to_cloud_task", max_retries=2, time_limit=900)
def upload_to_cloud_task(self, previous_result: dict, bookmark_id: str, user_id: str):
    """
    FASE 3.4: Upload de vídeo pra Supabase Storage
    - Baixa vídeo via Apify
    - Upload do vídeo pra Supabase Storage
    - Gerar Signed URL
    - Atualizar database
    """
    logger.info(f"☁️ Upload pra cloud - Bookmark: {bookmark_id}")

    temp_video_path = None

    try:
        url = previous_result.get('url')
        if not url:
            raise Exception("URL não disponível para upload de vídeo")

        # 1. Obter URL de download do vídeo
        download_url = previous_result.get('video_download_url')

        if download_url:
            logger.info(f"♻️ Reusando video_download_url do pipeline (sem chamada extra Apify)")
        else:
            # Fallback: buscar via Apify (só se pipeline não passou a URL)
            logger.info("⬇️ Baixando URL via Apify (fallback)...")
            loop = asyncio.get_event_loop()
            from models import Platform
            platform = apify_service.detect_platform(url)

            if platform == Platform.YOUTUBE:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_youtube(url, quality="720p")
                )
            elif platform == Platform.INSTAGRAM:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_instagram(url, quality="720p")
                )
            elif platform == Platform.TIKTOK:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_tiktok(url, quality="720p")
                )
            elif platform == Platform.X:
                video_data = loop.run_until_complete(
                    apify_service.extract_video_download_url_x(url, quality="720p")
                )
            else:
                raise Exception(f"Plataforma não suportada: {platform}")

            if not video_data or not video_data.get('download_url'):
                raise Exception("Falha ao extrair URL do vídeo")

            download_url = video_data['download_url']

        logger.info(f"✅ URL obtida: {download_url[:80]}...")

        # 2. Baixar vídeo para arquivo temporário
        import httpx
        logger.info("⬇️ Baixando vídeo...")

        temp_video_path = f"/tmp/{bookmark_id}.mp4"
        with httpx.stream("GET", download_url, timeout=180.0, follow_redirects=True) as response:
            response.raise_for_status()
            with open(temp_video_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        file_size_bytes = os.path.getsize(temp_video_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info(f"✅ Vídeo baixado: {file_size_mb:.2f}MB")

        # 3. Upload para Supabase Storage
        logger.info("☁️ Fazendo upload para Supabase Storage...")

        cloud_path = f"{user_id}/{bookmark_id}.mp4"
        with open(temp_video_path, "rb") as video_file:
            supabase_client.storage.from_("user-videos").upload(
                path=cloud_path,
                file=video_file,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )

        logger.info(f"✅ Upload concluído: {cloud_path}")

        # 4. Gerar Signed URL (válida por 1 ano)
        signed_url_data = supabase_client.storage.from_("user-videos").create_signed_url(
            path=cloud_path,
            expires_in=31536000  # 1 ano
        )

        cloud_url = signed_url_data.get("signedURL") if signed_url_data else None
        if not cloud_url:
            raise Exception("Falha ao gerar Signed URL")

        logger.info(f"✅ Signed URL gerada: {cloud_url[:80]}...")

        # 5. Atualizar database
        logger.info("💾 Atualizando Supabase com cloud URL...")

        supabase_client.table('bookmarks').update({
            'cloud_video_url': cloud_url,
            'cloud_upload_status': 'completed',
            'cloud_uploaded_at': datetime.utcnow().isoformat(),
            'cloud_file_size_bytes': file_size_bytes,
        }).eq('id', bookmark_id).execute()

        logger.info(f"✅ Database atualizado - Bookmark: {bookmark_id}")

        return {
            **previous_result,
            "cloud_uploaded": True,
            "cloud_video_url": cloud_url,
            "cloud_file_size_mb": file_size_mb
        }

    except Exception as e:
        logger.error(f"❌ Erro ao fazer upload pra cloud - Bookmark: {bookmark_id}, Erro: {str(e)}")

        # Atualizar status no Supabase
        supabase_client.table('bookmarks').update({
            'cloud_upload_status': 'failed',
        }).eq('id', bookmark_id).execute()

        update_bookmark_status(bookmark_id, "failed", self.request.id, f"Erro no upload cloud: {str(e)}")

        # Retry se for erro temporário
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            raise self.retry(exc=e, countdown=90)  # Retry após 90s

        raise

    finally:
        # Cleanup: deletar vídeo temporário
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.unlink(temp_video_path)
                logger.info(f"🗑️ Vídeo temporário deletado: {temp_video_path}")
            except:
                pass


@celery_app.task(bind=True, name="tasks.generate_embedding_task", max_retries=2, time_limit=60)
def generate_embedding_task(self, previous_result: dict, bookmark_id: str, user_id: str):
    """
    FASE 3.4: Gerar embedding semântico
    - Combina smart_title + auto_tags + auto_categories + transcription + multimodal_analysis
    - Gera vetor de 768 dimensões via Gemini Embedding API
    - Salva no Supabase (coluna embedding)
    """
    timer = TaskTimer("EMBEDDING", bookmark_id)
    timer.start()

    try:
        # 1. Buscar dados do bookmark no Supabase
        logger.debug(f"Buscando dados do bookmark para embedding...")

        response = supabase_client.table('bookmarks').select(
            'smart_title, auto_tags, auto_categories, video_transcript, visual_analysis'
        ).eq('id', bookmark_id).single().execute()

        if not response.data:
            raise Exception("Bookmark não encontrado no Supabase")

        bookmark = response.data

        # 2. Gerar embedding
        logger.info(f"📊 Gerando embedding...")

        embedding = embedding_service.generate_from_bookmark_dict(bookmark)

        if not embedding:
            raise Exception("Embedding service retornou None")

        # 3. Salvar no Supabase
        supabase_client.table('bookmarks').update({
            'embedding': embedding
        }).eq('id', bookmark_id).execute()

        # Log consolidado de sucesso
        timer.success(
            Dimensões=len(embedding),
            Campos=f"SmartTitle={'✓' if bookmark.get('smart_title') else '✗'} Tags={len(bookmark.get('auto_tags', []))}"
        )

        # 4. Retornar dados para próxima task
        return {
            **previous_result,
            "embedding_generated": True,
            "embedding_dimensions": len(embedding)
        }

    except Exception as e:
        timer.error(f"Embedding: {str(e)[:60]}")

        # Retry se for erro temporário
        if "timeout" in str(e).lower() or "rate limit" in str(e).lower():
            logger.warning(f"⚠️ Retry após 30s (timeout/rate limit)")
            raise self.retry(exc=e, countdown=30)

        # Não falhar o bookmark inteiro se embedding falhar
        logger.warning(f"⚠️ Embedding falhou (não crítico) - continuando pipeline")
        return {
            **previous_result,
            "embedding_generated": False,
            "embedding_error": str(e)[:100]
        }


@celery_app.task(bind=True, name="tasks.cleanup_and_notify_task")
def cleanup_and_notify_task(self, previous_result: dict, bookmark_id: str, user_id: str):
    """
    FASE 3.5: Cleanup e notificação
    - Deletar arquivos temporários
    - Atualizar status: processing → completed
    - Notificar celular (opcional: push notification)
    """
    logger.info(f"🧹 Cleanup e notificação - Bookmark: {bookmark_id}")

    try:
        # 1. Cleanup de arquivos temporários
        logger.info("🗑️ Limpando arquivos temporários...")

        temp_patterns = [
            f"/tmp/{bookmark_id}*",
            f"/tmp/video_{bookmark_id}*",
            f"/tmp/thumb_{bookmark_id}*",
        ]

        import glob
        for pattern in temp_patterns:
            for file_path in glob.glob(pattern):
                try:
                    os.unlink(file_path)
                    logger.debug(f"Deletado: {file_path}")
                except:
                    pass

        # 2. Atualizar status final no Supabase
        update_bookmark_status(bookmark_id, "completed", self.request.id, error_message=None)

        # 3. LOG RESUMO FINAL (uma linha com tudo - ordem de execução)
        pipeline_summary = []
        if previous_result.get('metadata_extracted'):
            pipeline_summary.append("Metadata:✓")
        if previous_result.get('cloud_uploaded'):
            pipeline_summary.append("Upload:✓")
        if previous_result.get('video_analyzed'):
            pipeline_summary.append("Gemini:✓")
        if previous_result.get('ai_processed'):
            pipeline_summary.append("Gemini Pro:✓")

        tags_count = len(previous_result.get('auto_tags', []))
        cats_count = len(previous_result.get('auto_categories', []))

        logger.info(
            f"🎉 [PIPELINE] {bookmark_id} - COMPLETO | "
            f"{' '.join(pipeline_summary)} | "
            f"Tags: {tags_count} | Categorias: {cats_count}"
        )

        # 4. (Opcional) Enviar notificação push
        # TODO: Implementar quando tiver Firebase Cloud Messaging

        return {
            **previous_result,
            "cleanup_done": True,
            "status": "completed",
            "message": "Processamento concluído com sucesso!"
        }

    except Exception as e:
        logger.error(f"❌ Erro no cleanup - Bookmark: {bookmark_id}, Erro: {str(e)}")
        # Não falha o processamento inteiro por erro no cleanup
        return {
            **previous_result,
            "cleanup_done": False,
            "status": "completed",  # Marca como completed mesmo assim
            "message": f"Processamento concluído mas cleanup falhou: {str(e)}"
        }


# ============================================================================
# AUTO-SYNC (cron job diário)
# ============================================================================

MAX_SYNC_RETRIES = 3  # Após 3 tentativas, para de tentar
MAX_SYNC_BATCH = 5    # Máximo de bookmarks por sync (economiza créditos)


def _get_sync_redis():
    """Redis client síncrono para controle de retries do auto-sync"""
    import redis as sync_redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return sync_redis.from_url(redis_url)


@celery_app.task(bind=True, name="tasks.auto_sync_incomplete_bookmarks_task")
def auto_sync_incomplete_bookmarks_task(self):
    """
    Auto-sync de bookmarks incompletos (cron job diário às 3h)
    Proteções:
    - Retry count via Redis (max 3 tentativas por bookmark)
    - Após 3 falhas: marca failed com mensagem e para de tentar
    - Máximo 5 bookmarks por sync (economiza créditos Apify)
    - Só busca status failed/pending (não pega completed com dados parciais)
    """
    logger.info("🔄 Iniciando auto-sync diário de bookmarks incompletos")

    try:
        rc = _get_sync_redis()

        # 1. Buscar apenas bookmarks failed/pending
        logger.info("🔍 Buscando bookmarks failed/pending no Supabase...")
        incomplete_bookmarks = supabase_client.table('bookmarks').select(
            'id, url, user_id, metadata, auto_tags, cloud_video_url, video_transcript, processing_status'
        ).or_(
            'processing_status.eq.failed,'
            'processing_status.eq.pending'
        ).execute()

        bookmarks = incomplete_bookmarks.data if incomplete_bookmarks else []
        logger.info(f"📊 Encontrados {len(bookmarks)} bookmarks failed/pending")

        if not bookmarks:
            logger.info("✅ Nenhum bookmark incompleto")
            return {"success": True, "processed": 0, "skipped_max_retries": 0}

        # 2. Filtrar por retry count
        eligible = []
        skipped_retries = 0

        for bookmark in bookmarks:
            bid = bookmark['id']
            retry_key = f"sync_retry:{bid}"
            retries = int(rc.get(retry_key) or 0)

            if retries >= MAX_SYNC_RETRIES:
                logger.warning(f"💀 {bid[:8]}: {retries} retries atingido - desistindo")
                # Atualizar erro no banco (para o usuário saber)
                supabase_client.table('bookmarks').update({
                    'error_message': f'Auto-sync desistiu após {retries} tentativas. Reprocessamento manual necessário.'
                }).eq('id', bid).execute()
                skipped_retries += 1
                continue

            eligible.append((bookmark, retries))

        logger.info(f"📊 Elegíveis: {len(eligible)} | Max retries atingido: {skipped_retries}")

        if not eligible:
            return {"success": True, "processed": 0, "skipped_max_retries": skipped_retries}

        # 3. Limitar batch
        to_process = eligible[:MAX_SYNC_BATCH]
        logger.info(f"⚙️ Processando {len(to_process)}/{len(eligible)} (cap: {MAX_SYNC_BATCH})")

        processed_count = 0
        for bookmark, retries in to_process:
            bid = bookmark['id']
            url = bookmark['url']
            user_id = bookmark['user_id']

            # Incrementar retry count (TTL 30 dias)
            retry_key = f"sync_retry:{bid}"
            new_count = rc.incr(retry_key)
            rc.expire(retry_key, 30 * 86400)
            logger.info(f"📝 {bid[:8]}: tentativa {new_count}/{MAX_SYNC_RETRIES} - {url[:50]}")

            has_metadata = bookmark.get('metadata') is not None
            has_ai = bool(bookmark.get('auto_tags'))
            has_cloud_video = bool(bookmark.get('cloud_video_url'))
            has_analysis = bool(bookmark.get('video_transcript'))

            try:
                process_bookmark_complete_task.apply_async(
                    kwargs={
                        'bookmark_id': bid,
                        'url': url,
                        'user_id': user_id,
                        'extract_metadata': not has_metadata,
                        'analyze_video': has_cloud_video and not has_analysis,
                        'process_ai': not has_ai,
                        'upload_to_cloud': False,
                    },
                    retry=False
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"❌ Erro ao enfileirar {bid[:8]}: {str(e)}")

        logger.info(f"🎉 Auto-sync: {processed_count} enfileirados, {skipped_retries} desistidos")

        return {
            "success": True,
            "total_found": len(bookmarks),
            "processed": processed_count,
            "skipped_max_retries": skipped_retries,
            "message": f"Auto-sync: {processed_count} enfileirados, {skipped_retries} desistidos"
        }

    except Exception as e:
        logger.error(f"❌ Erro no auto-sync diário: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Erro no auto-sync diário"
        }


@celery_app.task(bind=True, name="tasks.cleanup_temp_files_task")
def cleanup_temp_files_task(self):
    """
    Cleanup de arquivos temporários (roda a cada 6 horas)
    - Deleta vídeos temporários mais antigos que 24h
    - Deleta thumbnails temporários
    """
    logger.info("🧹 Cleanup de arquivos temporários")

    # TODO: Implementar
    return {
        "success": True,
        "files_deleted": 0
    }


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def update_bookmark_status(
    bookmark_id: str,
    status: str,
    job_id: Optional[str] = None,
    error_message: Optional[str] = None
):
    """
    Atualiza status de processamento no Supabase

    Args:
        bookmark_id: UUID do bookmark
        status: queued | processing | completed | failed
        job_id: ID do job Celery
        error_message: Mensagem de erro (se falhou)
    """
    # TODO: Implementar na FASE 6.1 (após migration de campos)
    logger.info(f"📝 Status atualizado: {bookmark_id} → {status}")
    pass
