from dotenv import load_dotenv
import os

# IMPORTANTE: Carregar .env ANTES de importar os serviços
load_dotenv()

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import logging
from models import VideoMetadata, Platform
from services.apify_service import ApifyService
from services.whisper_service import whisper_service
from services.claude_service import claude_service
from services.chat_service import chat_with_ai, find_similar_bookmarks
from services.transcoding_service import TranscodingService
from services.thumbnail_service import ThumbnailService
from services.video_analysis_service import video_analysis_service
from supabase import create_client, Client

# Background processor (FastAPI Background Tasks - substitui Celery)
from background_processor import process_bookmark_background

# Configurar logging
logging.basicConfig(level=logging.DEBUG)  # DEBUG temporário para diagnosticar fluxo Gemini→Claude
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Refs Metadata API",
    description="API para extração de metadados de vídeos do YouTube, TikTok e Instagram",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

apify_service = ApifyService()
transcoding_service = TranscodingService()

# Inicializar Supabase client para ThumbnailService
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase_client: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
thumbnail_service = ThumbnailService(supabase_client) if supabase_client else None


class ExtractRequest(BaseModel):
    url: str
    user_id: Optional[str] = None  # Para upload de thumbnail na cloud
    bookmark_id: Optional[str] = None  # Para upload de thumbnail na cloud


class ExtractResponse(BaseModel):
    success: bool
    metadata: VideoMetadata = None  # Renomeado de 'data' para 'metadata' (compatibilidade com Flutter)
    error: str = None


class ProcessContextResponse(BaseModel):
    success: bool
    transcribed_text: Optional[str] = None
    context_processed: Optional[str] = None
    tags: Optional[List[str]] = None
    suggested_categories: Optional[List[str]] = None
    suggested_projects: Optional[List[str]] = None
    search_keywords: Optional[List[str]] = None
    confidence: Optional[str] = None
    error: Optional[str] = None


class ProcessMetadataAutoRequest(BaseModel):
    title: str
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None
    top_comments: Optional[List[dict]] = None
    local_video_path: Optional[str] = None  # Caminho do vídeo local para análise (transcrição + visual)
    cloud_video_url: Optional[str] = None  # URL do vídeo na cloud (Supabase) - será baixado temporariamente
    user_context: Optional[str] = None  # Contexto manual do usuário (peso máximo na análise!)


class ProcessMetadataAutoResponse(BaseModel):
    success: bool
    auto_description: Optional[str] = None
    auto_tags: Optional[List[str]] = None
    auto_categories: Optional[List[str]] = None
    confidence: Optional[str] = None
    relevance_score: Optional[float] = None
    video_transcript: Optional[str] = None  # Transcrição do áudio (Whisper)
    visual_analysis: Optional[str] = None   # Análise visual (GPT-4 Vision)
    transcript_language: Optional[str] = None  # Idioma detectado
    video_transcript_pt: Optional[str] = None  # Tradução PT da transcrição
    visual_analysis_pt: Optional[str] = None  # Tradução PT da análise visual
    filtered_comments: Optional[List[dict]] = None  # 50 melhores comentários filtrados
    error: Optional[str] = None


class ExtractVideoUrlRequest(BaseModel):
    url: str
    quality: Optional[str] = "480p"  # 360p, 480p, 720p
    transcode: Optional[bool] = False  # Se True, transcodifica para H.264 Baseline (lento mas compatível)


class ExtractVideoUrlResponse(BaseModel):
    success: bool
    download_url: Optional[str] = None
    expires_in_hours: Optional[int] = None
    file_size_mb: Optional[float] = None
    quality: Optional[str] = None
    platform: Optional[str] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Video Refs Metadata API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/debug/apify-status")
async def debug_apify_status():
    """Temporário: verifica estado dos tokens Apify"""
    import os
    token_raw = os.getenv("APIFY_TOKEN", "")

    # Checar blacklist no Redis
    blacklisted = []
    try:
        rc = await apify_service.get_redis_client()
        for i in range(len(apify_service.clients)):
            is_dead = await rc.exists(f"apify:dead_token:{i}")
            if is_dead:
                blacklisted.append(i)
    except Exception as e:
        blacklisted = [f"redis_error: {str(e)[:50]}"]

    # Checar cache pra URL de teste
    cache_keys = []
    try:
        rc = await apify_service.get_redis_client()
        for key in ["instagram:https://www.instagram.com/p/DIMT3feMPNL/",
                     "instagram:https://www.instagram.com/p/DIMb1r0sRvK/"]:
            val = await rc.get(key)
            cache_keys.append({"key": key, "cached": bool(val), "preview": str(val)[:100] if val else None})
    except: pass

    return {
        "token_configured": bool(token_raw),
        "token_prefix": token_raw[:15] + "..." if token_raw else "EMPTY",
        "tokens_count": len(apify_service.apify_tokens),
        "clients_count": len(apify_service.clients),
        "current_index": apify_service._current_client_index,
        "apify_token_attr": bool(apify_service.apify_token),
        "blacklisted_tokens": blacklisted,
        "cache_check": cache_keys,
    }


@app.get("/api/youtube-cookies-status")
async def youtube_cookies_status():
    """Verifica se cookies do YouTube estao validos."""
    try:
        rc = await apify_service.get_redis_client()
        expired = await rc.exists("youtube:cookies_expired")
        # Checar se cookies existem no Storage
        from supabase import create_client as _sb
        sb_url = os.getenv("SUPABASE_URL")
        sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        has_cookies = False
        meta = None
        if sb_url and sb_key:
            sb = _sb(sb_url, sb_key)
            try:
                m = sb.storage.from_("thumbnails").download("system/youtube_cookies_meta.json")
                if m:
                    import json as _j
                    meta = _j.loads(m)
                    has_cookies = True
            except:
                pass
        return {
            "cookies_uploaded": has_cookies,
            "cookies_expired": bool(expired),
            "exported_at": meta.get("exported_at") if meta else None,
            "action_needed": "Rode: python3 export_youtube_cookies.py" if (expired or not has_cookies) else None,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/debug/test-ytdlp")
async def debug_test_ytdlp():
    """Temporário: testa yt-dlp com cookies do Supabase"""
    import subprocess
    try:
        ver = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        version = ver.stdout.strip() if ver.returncode == 0 else f"erro: {ver.stderr[:50]}"

        # Baixar cookies
        cookies_path = await apify_service._get_youtube_cookies_path()

        # Testar com cookies
        cmd = ["yt-dlp", "--get-url", "-f", "best[ext=mp4]/best", "--no-warnings"]
        if cookies_path:
            cmd.extend(["--cookies", cookies_path])
        cmd.append("https://www.youtube.com/shorts/SB-rfAuNkHE")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        url_ok = bool(result.returncode == 0 and result.stdout.strip())
        return {
            "yt_dlp_version": version,
            "cookies_loaded": bool(cookies_path),
            "test_url_extracted": url_ok,
            "url_preview": result.stdout.strip()[:80] if url_ok else None,
            "error": result.stderr[:150] if not url_ok else None,
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/debug/clear-blacklist")
async def debug_clear_blacklist():
    """Temporário: limpa blacklist de tokens mortos no Redis"""
    try:
        rc = await apify_service.get_redis_client()
        cleared = 0
        for i in range(10):  # limpa até 10 slots
            key = f"apify:dead_token:{i}"
            if await rc.exists(key):
                await rc.delete(key)
                cleared += 1
        return {"success": True, "cleared": cleared}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/extract-metadata", response_model=ExtractResponse)
async def extract_metadata(request: ExtractRequest):
    """
    Extrai metadados de vídeos do YouTube, TikTok e Instagram.

    Parâmetros:
    - url: URL do vídeo para extrair metadados
    - user_id: ID do usuário (opcional, para upload de thumbnail permanente)
    - bookmark_id: ID do bookmark (opcional, para upload de thumbnail permanente)

    Retorna:
    - VideoMetadata com todos os dados extraídos
    - Se user_id e bookmark_id forem fornecidos, faz upload da thumbnail para Supabase Storage
    - Cache automático por 7 dias
    """
    try:
        if not request.url:
            raise HTTPException(status_code=400, detail="URL é obrigatória")

        metadata = await apify_service.extract_metadata(request.url)

        # Se user_id e bookmark_id foram fornecidos E thumbnail_service está disponível,
        # faz upload da thumbnail para Supabase Storage
        if (request.user_id and request.bookmark_id and
            thumbnail_service and metadata.thumbnail_url):

            logger.info(f"📸 Fazendo upload de thumbnail para bookmark {request.bookmark_id}")

            cloud_thumbnail_url = await thumbnail_service.upload_thumbnail(
                thumbnail_url=metadata.thumbnail_url,
                user_id=request.user_id,
                bookmark_id=request.bookmark_id
            )

            if cloud_thumbnail_url:
                metadata.cloud_thumbnail_url = cloud_thumbnail_url
                logger.info(f"✅ Thumbnail permanente criada: {cloud_thumbnail_url[:80]}...")
            else:
                logger.warning("⚠️ Falha ao fazer upload de thumbnail, usando URL original")

        return ExtractResponse(
            success=True,
            metadata=metadata  # Campo renomeado para compatibilidade com Flutter
        )

    except ValueError as e:
        return ExtractResponse(
            success=False,
            error=str(e)
        )

    except Exception as e:
        return ExtractResponse(
            success=False,
            error=f"Erro interno: {str(e)}"
        )


@app.post("/api/process-context", response_model=ProcessContextResponse)
async def process_context(
    url: str = Form(...),
    text_context: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    video_title: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    user_categories: Optional[str] = Form(None),  # JSON string de array
    user_projects: Optional[str] = Form(None)  # JSON string de array
):
    """
    Processa contexto do usuário (texto ou áudio) com IA.

    Aceita:
    - text_context: Texto digitado pelo usuário (opcional)
    - audio_file: Arquivo de áudio para transcrever (opcional)
    - url: URL do vídeo
    - video_title, platform, author: Metadados do vídeo (opcional)
    - user_categories, user_projects: Listas existentes do usuário (JSON strings)

    Retorna:
    - Contexto processado, tags, categorias e projetos sugeridos
    """
    try:
        import json

        # Parse user categories e projects
        categories_list = json.loads(user_categories) if user_categories else []
        projects_list = json.loads(user_projects) if user_projects else []

        context_text = text_context
        transcription = None

        # Se tem áudio, transcrever primeiro
        if audio_file:
            logger.info(f"🎤 Recebido áudio: {audio_file.filename}")

            if not whisper_service.is_available():
                return ProcessContextResponse(
                    success=False,
                    error="Whisper API não configurada (OPENAI_API_KEY faltando)"
                )

            # Salvar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as tmp_file:
                content = await audio_file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name

            try:
                # Transcrever
                transcription = await whisper_service.transcribe_audio(tmp_path)
                if not transcription:
                    return ProcessContextResponse(
                        success=False,
                        error="Falha ao transcrever áudio"
                    )

                context_text = transcription
                logger.info(f"✅ Transcrição: {transcription[:100]}...")

            finally:
                # Limpar arquivo temporário
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        # Se não tem contexto (nem texto nem áudio), retornar erro
        if not context_text:
            return ProcessContextResponse(
                success=False,
                error="Necessário fornecer text_context ou audio_file"
            )

        # Processar contexto com Claude
        if not claude_service.is_available():
            logger.warning("Claude API não configurada, retornando só transcrição")
            return ProcessContextResponse(
                success=True,
                transcribed_text=transcription,
                context_processed=context_text,
                tags=[],
                suggested_categories=[],
                suggested_projects=[],
                search_keywords=[],
                confidence="low"
            )

        # Processar com Claude
        logger.info("🧠 Processando contexto com Claude...")
        result = await claude_service.process_context(
            user_context_raw=context_text,
            video_title=video_title or "",
            platform=platform or "",
            author=author or "",
            user_categories=categories_list,
            user_projects=projects_list
        )

        if not result:
            logger.warning("Claude não retornou resultado, usando fallback")
            return ProcessContextResponse(
                success=True,
                transcribed_text=transcription,
                context_processed=context_text,
                tags=[],
                suggested_categories=[],
                suggested_projects=[],
                search_keywords=[],
                confidence="low"
            )

        # Retornar sucesso com resultado processado
        return ProcessContextResponse(
            success=True,
            transcribed_text=transcription,
            context_processed=result.get("context_processed"),
            tags=result.get("tags", []),
            suggested_categories=result.get("suggested_categories", []),
            suggested_projects=result.get("suggested_projects", []),
            search_keywords=result.get("search_keywords", []),
            confidence=result.get("confidence", "medium")
        )

    except json.JSONDecodeError:
        return ProcessContextResponse(
            success=False,
            error="user_categories ou user_projects não são JSON válidos"
        )
    except Exception as e:
        logger.error(f"❌ Erro em process_context: {str(e)}")
        return ProcessContextResponse(
            success=False,
            error=f"Erro interno: {str(e)}"
        )


@app.post("/api/process-metadata-auto", response_model=ProcessMetadataAutoResponse)
async def process_metadata_auto(request: ProcessMetadataAutoRequest):
    """
    Processa metadados do vídeo automaticamente (sem contexto do usuário).

    Analisa título, descrição, hashtags e comentários com Claude para gerar:
    - auto_description: Resumo automático do vídeo
    - auto_tags: Tags extraídas dos metadados
    - auto_categories: Categorias sugeridas

    Se local_video_path for fornecido, também analisa o vídeo:
    - Transcrição de áudio (Whisper API)
    - Análise visual de frames (GPT-4 Vision)

    Usado quando usuário pula a captura de contexto.
    """
    try:
        if not request.title or not request.title.strip():
            return ProcessMetadataAutoResponse(
                success=False,
                error="Título é obrigatório"
            )

        # Verificar se Claude está disponível
        if not claude_service.is_available():
            logger.warning("Claude API não configurada, pulando processamento automático")
            return ProcessMetadataAutoResponse(
                success=False,
                error="Claude API não configurada"
            )

        # Analisar vídeo se caminho foi fornecido
        video_transcript = ""
        visual_analysis = ""
        transcript_language = ""
        video_transcript_pt = None
        visual_analysis_pt = None
        temp_video_file = None

        # Análise multimodal (Whisper + GPT-4 Vision)
        video_path_for_analysis = None
        if request.local_video_path:
            video_path_for_analysis = request.local_video_path
        elif request.cloud_video_url:
            # Baixa temporariamente da cloud
            logger.info(f"☁️ Baixando vídeo temporariamente da cloud: {request.cloud_video_url[:80]}...")
            try:
                import httpx
                import tempfile

                async with httpx.AsyncClient(timeout=180.0) as client:
                    response = await client.get(request.cloud_video_url)
                    response.raise_for_status()
                    video_data = response.content

                temp_video_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                temp_video_file.write(video_data)
                temp_video_file.close()

                video_path_for_analysis = temp_video_file.name
                size_mb = len(video_data) / (1024 * 1024)
                logger.info(f"✅ Vídeo baixado temporariamente: {size_mb:.2f} MB")
            except Exception as e:
                logger.error(f"❌ Erro ao baixar vídeo da cloud: {str(e)}")
                video_path_for_analysis = None

        if video_path_for_analysis and video_analysis_service.is_available():
            logger.info(f"🎬 Analisando vídeo: {video_path_for_analysis}")
            video_analysis = await video_analysis_service.analyze_video(video_path_for_analysis)

            if video_analysis:
                video_transcript = video_analysis.get("transcript", "")
                visual_analysis = video_analysis.get("visual_analysis", "")
                transcript_language = video_analysis.get("language", "")
                video_transcript_pt = video_analysis.get("transcript_pt")
                visual_analysis_pt = video_analysis.get("visual_analysis_pt")
                logger.info(f"✅ Análise de vídeo concluída - Transcript: {len(video_transcript)} chars, Visual: {len(visual_analysis)} chars")
                if video_transcript_pt:
                    logger.info(f"🌐 Tradução PT (Transcrição): {len(video_transcript_pt)} chars")
                if visual_analysis_pt:
                    logger.info(f"🌐 Tradução PT (Visual): {len(visual_analysis_pt)} chars")
            else:
                logger.warning("⚠️ Análise de vídeo falhou, continuando sem transcrição/visual")

            # Limpa arquivo temporário
            if temp_video_file and os.path.exists(temp_video_file.name):
                try:
                    os.unlink(temp_video_file.name)
                    logger.info(f"🧹 Arquivo temporário removido")
                except Exception as e:
                    logger.warning(f"⚠️ Não foi possível remover arquivo temporário: {e}")

        # Processar metadados com Claude (com transcript + visual + user_context)
        logger.info("🤖 Processando metadados automaticamente...")
        result = await claude_service.process_metadata_auto(
            title=request.title,
            description=request.description or "",
            hashtags=request.hashtags or [],
            top_comments=request.top_comments or [],
            video_transcript=video_transcript,
            visual_analysis=visual_analysis,
            user_context=request.user_context or ""  # ⭐ PRIORIDADE MÁXIMA (40% de peso)
        )

        if not result:
            logger.warning("Claude não retornou resultado para processamento automático")
            return ProcessMetadataAutoResponse(
                success=False,
                error="Falha ao processar metadados"
            )

        # Retornar sucesso com resultado processado
        return ProcessMetadataAutoResponse(
            success=True,
            auto_description=result.get("auto_description"),
            auto_tags=result.get("auto_tags", []),
            auto_categories=result.get("auto_categories", []),
            confidence=result.get("confidence", "medium"),
            relevance_score=result.get("relevance_score", 0.5),
            video_transcript=video_transcript if video_transcript else None,
            visual_analysis=visual_analysis if visual_analysis else None,
            transcript_language=transcript_language if transcript_language else None,
            video_transcript_pt=video_transcript_pt,
            visual_analysis_pt=visual_analysis_pt,
            filtered_comments=result.get("filtered_comments", [])
        )

    except Exception as e:
        logger.error(f"❌ Erro em process_metadata_auto: {str(e)}")
        return ProcessMetadataAutoResponse(
            success=False,
            error=f"Erro interno: {str(e)}"
        )


# ============================================================
# CHAT IA - Busca Semântica Conversacional
# ============================================================

class ChatMessage(BaseModel):
    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = None
    max_results: Optional[int] = 10


class ChatResponse(BaseModel):
    success: bool
    message: str = None
    bookmarks: List[dict] = []
    total_found: int = 0
    error: str = None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint de chat conversacional com IA.

    Usa busca semântica (embeddings) + Claude API para responder
    perguntas sobre bookmarks de forma natural e contextual.

    Exemplos de uso:
    - "Preciso de vídeos com transições cinematográficas escuras"
    - "Mostre refs de campanhas de Natal urbano"
    - "Quero ver efeitos de água ou líquidos"
    """
    try:
        logger.info(f"💬 Chat request: '{request.message}'")

        # Converte histórico de conversa para formato do serviço
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Chama serviço de chat
        result = await chat_with_ai(
            user_message=request.message,
            conversation_history=history,
            max_bookmarks=request.max_results or 10
        )

        return ChatResponse(
            success=True,
            message=result["message"],
            bookmarks=result["bookmarks"],
            total_found=result["total_found"]
        )

    except Exception as e:
        logger.error(f"❌ Erro em /api/chat: {str(e)}")
        return ChatResponse(
            success=False,
            error=f"Erro ao processar chat: {str(e)}"
        )


@app.post("/api/transcribe-audio")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Endpoint simples para transcrever áudio usando Whisper API.

    Usado no chat para converter mensagens de voz em texto.
    """
    try:
        logger.info(f"🎤 Transcrevendo áudio: {audio_file.filename}")

        # Salva arquivo temporário
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Transcreve com Whisper
        from services.whisper_service import WhisperService
        whisper = WhisperService()
        transcription = await whisper.transcribe_audio(temp_path, language="pt")

        # Remove arquivo temporário
        import os
        os.remove(temp_path)

        if transcription:
            logger.info(f"✅ Transcrição: {transcription[:100]}...")
            return {"success": True, "transcription": transcription}
        else:
            logger.error("❌ Falha na transcrição")
            return {"success": False, "error": "Falha ao transcrever áudio"}

    except Exception as e:
        logger.error(f"❌ Erro em /api/transcribe-audio: {str(e)}")
        return {"success": False, "error": f"Erro ao transcrever: {str(e)}"}


# ============================================================
# ANÁLISE MULTIMODAL DE VÍDEO (Whisper + GPT-4 Vision)
# ============================================================

class AnalyzeVideoRequest(BaseModel):
    cloud_video_url: str


class AnalyzeVideoResponse(BaseModel):
    success: bool
    video_transcript: Optional[str] = None
    visual_analysis: Optional[str] = None
    transcript_language: Optional[str] = None
    error: Optional[str] = None


@app.post("/api/analyze-video", response_model=AnalyzeVideoResponse)
async def analyze_video(request: AnalyzeVideoRequest):
    """
    Analisa vídeo que já está na cloud (Whisper + GPT-4 Vision).

    Fluxo:
    1. Baixa vídeo temporariamente da cloud URL
    2. Extrai áudio e analisa com Whisper
    3. Extrai frames e analisa com GPT-4 Vision
    4. Retorna transcrição, análise visual e idioma
    """
    import httpx

    try:
        logger.info(f"🎬 Analisando vídeo da cloud: {request.cloud_video_url[:50]}...")

        if not video_analysis_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Serviço de análise multimodal não disponível (OPENAI_API_KEY não configurada)"
            )

        # 1. Baixar vídeo temporariamente
        logger.info(f"⬇️  Baixando vídeo da cloud...")
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.get(request.cloud_video_url)
            response.raise_for_status()
            video_data = response.content

        # 2. Salvar em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
            temp_video.write(video_data)
            temp_video_path = temp_video.name

        logger.info(f"✅ Vídeo baixado: {len(video_data) / (1024 * 1024):.2f}MB")

        # 3. Analisar vídeo (Whisper + GPT-4 Vision)
        logger.info(f"🎤🖼️  Analisando com Whisper + GPT-4 Vision...")
        analysis_result = await video_analysis_service.analyze_video(temp_video_path)

        # 4. Limpar arquivo temporário
        try:
            os.unlink(temp_video_path)
        except:
            pass

        if not analysis_result:
            raise HTTPException(status_code=500, detail="Análise multimodal falhou")

        logger.info(f"✅ Análise multimodal concluída!")
        logger.info(f"   - Transcrição: {len(analysis_result.get('transcript', ''))} chars ({analysis_result.get('language', 'N/A')})")
        logger.info(f"   - Análise Visual: {len(analysis_result.get('visual_analysis', ''))} chars")

        return {
            "success": True,
            "video_transcript": analysis_result.get("transcript"),
            "visual_analysis": analysis_result.get("visual_analysis"),
            "transcript_language": analysis_result.get("language"),
        }

    except httpx.HTTPError as e:
        logger.error(f"❌ Erro ao baixar vídeo da cloud: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao baixar vídeo: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Erro ao analisar vídeo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao analisar vídeo: {str(e)}")


# ============================================================
# BUSCA POR SIMILARIDADE
# ============================================================

class FindSimilarRequest(BaseModel):
    bookmark_id: str
    user_id: str
    max_results: Optional[int] = 10


class FindSimilarResponse(BaseModel):
    success: bool
    bookmarks: List[dict] = []
    total_found: int = 0
    error: str = None


@app.post("/api/find-similar", response_model=FindSimilarResponse)
async def find_similar(request: FindSimilarRequest):
    """
    Encontra bookmarks similares a um bookmark específico.

    Usa busca semântica (embeddings) para encontrar vídeos com conteúdo,
    contexto, tags e categorias similares.

    Exemplos de uso:
    - Encontrar vídeos parecidos com um que o usuário gostou
    - Descobrir refs similares para expandir um projeto
    - Achar variações de uma técnica/estilo
    """
    try:
        logger.info(f"🔗 Find similar request para bookmark: {request.bookmark_id}")

        # Chama serviço de busca similar
        similar_bookmarks = await find_similar_bookmarks(
            bookmark_id=request.bookmark_id,
            user_id=request.user_id,
            max_results=request.max_results or 10,
            threshold=0.5
        )

        return FindSimilarResponse(
            success=True,
            bookmarks=similar_bookmarks,
            total_found=len(similar_bookmarks)
        )

    except Exception as e:
        logger.error(f"❌ Erro em /api/find-similar: {str(e)}")
        return FindSimilarResponse(
            success=False,
            error=f"Erro ao buscar similares: {str(e)}"
        )


@app.post("/api/extract-video-download-url", response_model=ExtractVideoUrlResponse)
async def extract_video_download_url(request: ExtractVideoUrlRequest):
    """
    Extrai URL direta do vídeo para download local no dispositivo do usuário.

    IMPORTANTE:
    - Backend NÃO armazena o vídeo
    - URL é temporária (válida por 2-6 horas dependendo da plataforma)
    - Apenas facilita a extração da URL de download
    - Usuário é responsável pelo download e armazenamento local

    Parâmetros:
    - url: URL do vídeo (YouTube, Instagram, TikTok)
    - quality: Qualidade desejada (360p, 480p, 720p) - padrão 480p

    Retorna:
    - download_url: URL direta temporária para download
    - expires_in_hours: Tempo de validade da URL
    - file_size_mb: Tamanho estimado do arquivo
    - quality: Qualidade real do vídeo
    - platform: Plataforma detectada
    """
    try:
        logger.info(f"📥 Extract video download URL request: {request.url} ({request.quality})")

        # Detecta plataforma
        platform = apify_service.detect_platform(request.url)
        logger.info(f"🎬 Plataforma detectada: {platform}")

        # Por enquanto, vamos usar apenas Instagram e TikTok
        # YouTube tem restrições de ToS mais severas

        if platform == Platform.INSTAGRAM:
            # Instagram: Extrai URL (e opcionalmente transcodifica para compatibilidade)
            try:
                # 1. Extrair URL original do Instagram
                video_data = await apify_service.extract_video_download_url_instagram(
                    request.url,
                    request.quality
                )

                logger.info(f"✅ URL de vídeo Instagram extraída: {video_data['download_url'][:50]}...")

                # 2. Se transcode=True, transcodifica para H.264 Baseline (lento mas compatível)
                if request.transcode:
                    logger.info(f"🎬 Transcodificação solicitada - garantindo compatibilidade...")
                    transcode_result = await transcoding_service.transcode_video(video_data["download_url"])

                    if not transcode_result["success"]:
                        raise ValueError(f"Falha na transcodificação: {transcode_result.get('error')}")

                    # Retornar URL do vídeo transcodificado
                    video_id = transcode_result["video_id"]
                    base_url = os.getenv("BASE_URL", "https://video-refs-backend.onrender.com")
                    transcoded_url = f"{base_url}/api/download-transcoded/{video_id}"

                    logger.info(f"✅ Vídeo transcodificado com sucesso: {video_id}")

                    return ExtractVideoUrlResponse(
                        success=True,
                        download_url=transcoded_url,
                        expires_in_hours=24,  # Vídeo fica armazenado por 24h no backend
                        file_size_mb=transcode_result["file_size_mb"],
                        quality="baseline_h264",  # Indica que foi transcodificado
                        platform="instagram"
                    )
                else:
                    # Sem transcodificação - retorna URL direta (rápido!)
                    logger.info(f"⚡ Retornando URL direta sem transcodificação (modo rápido)")

                    return ExtractVideoUrlResponse(
                        success=True,
                        download_url=video_data["download_url"],
                        expires_in_hours=video_data.get("expires_in_hours", 2),
                        file_size_mb=video_data.get("file_size_mb"),
                        quality=video_data.get("quality", "original"),
                        platform="instagram"
                    )

            except Exception as e:
                logger.error(f"❌ Erro ao processar Instagram: {str(e)}")
                return ExtractVideoUrlResponse(
                    success=False,
                    error=f"Erro ao extrair vídeo do Instagram: {str(e)}"
                )

        elif platform == Platform.TIKTOK:
            # TikTok: Extrai URL (e opcionalmente transcodifica para compatibilidade)
            try:
                # 1. Extrair URL original do TikTok
                video_data = await apify_service.extract_video_download_url_tiktok(
                    request.url,
                    request.quality
                )

                logger.info(f"✅ URL de vídeo TikTok extraída: {video_data['download_url'][:50]}...")

                # 2. Se transcode=True, transcodifica para H.264 Baseline (lento mas compatível)
                if request.transcode:
                    logger.info(f"🎬 Transcodificação solicitada - garantindo compatibilidade...")
                    transcode_result = await transcoding_service.transcode_video(video_data["download_url"])

                    if not transcode_result["success"]:
                        raise ValueError(f"Falha na transcodificação: {transcode_result.get('error')}")

                    # Retornar URL do vídeo transcodificado
                    video_id = transcode_result["video_id"]
                    base_url = os.getenv("BASE_URL", "https://video-refs-backend.onrender.com")
                    transcoded_url = f"{base_url}/api/download-transcoded/{video_id}"

                    logger.info(f"✅ Vídeo transcodificado com sucesso: {video_id}")

                    return ExtractVideoUrlResponse(
                        success=True,
                        download_url=transcoded_url,
                        expires_in_hours=24,  # Vídeo fica armazenado por 24h no backend
                        file_size_mb=transcode_result["file_size_mb"],
                        quality="baseline_h264",  # Indica que foi transcodificado
                        platform="tiktok"
                    )
                else:
                    # Sem transcodificação - retorna URL direta (rápido!)
                    logger.info(f"⚡ Retornando URL direta sem transcodificação (modo rápido)")

                    return ExtractVideoUrlResponse(
                        success=True,
                        download_url=video_data["download_url"],
                        expires_in_hours=video_data.get("expires_in_hours", 6),
                        file_size_mb=video_data.get("file_size_mb"),
                        quality=video_data.get("quality", "original"),
                        platform="tiktok"
                    )

            except Exception as e:
                logger.error(f"❌ Erro ao processar TikTok: {str(e)}")
                return ExtractVideoUrlResponse(
                    success=False,
                    error=f"Erro ao extrair vídeo do TikTok: {str(e)}"
                )

        elif platform == Platform.YOUTUBE:
            # YouTube: Por enquanto não suportado devido a ToS
            return ExtractVideoUrlResponse(
                success=False,
                platform="youtube",
                error="Download de vídeos do YouTube não é suportado devido às políticas de uso. "
                      "Você pode visualizar o vídeo direto no YouTube através do link."
            )

        else:
            return ExtractVideoUrlResponse(
                success=False,
                error=f"Plataforma não suportada: {platform}"
            )

    except Exception as e:
        logger.error(f"❌ Erro em /api/extract-video-download-url: {str(e)}")
        return ExtractVideoUrlResponse(
            success=False,
            error=f"Erro interno: {str(e)}"
        )


class TranscodeVideoRequest(BaseModel):
    source_url: str


class TranscodeVideoResponse(BaseModel):
    success: bool
    video_id: str = None
    file_size_mb: float = None
    error: str = None


@app.post("/api/transcode-video", response_model=TranscodeVideoResponse)
async def transcode_video_endpoint(request: TranscodeVideoRequest):
    """
    Transcodifica vídeo para H.264 Baseline Profile (compatível com Android).

    Args:
        source_url: URL do vídeo original

    Returns:
        video_id: ID para baixar o vídeo transcodificado via /api/download-transcoded/{video_id}
    """
    try:
        logger.info(f"🎬 Iniciando transcodificação de: {request.source_url[:50]}...")

        result = await transcoding_service.transcode_video(request.source_url)

        if result["success"]:
            logger.info(f"✅ Transcodificação concluída: {result['video_id']}")
            return TranscodeVideoResponse(
                success=True,
                video_id=result["video_id"],
                file_size_mb=result["file_size_mb"],
            )
        else:
            logger.error(f"❌ Erro na transcodificação: {result['error']}")
            return TranscodeVideoResponse(
                success=False,
                error=result["error"],
            )

    except Exception as e:
        logger.error(f"❌ Erro em /api/transcode-video: {str(e)}")
        return TranscodeVideoResponse(
            success=False,
            error=f"Erro interno: {str(e)}",
        )


@app.get("/api/download-transcoded/{video_id}")
async def download_transcoded_video(video_id: str):
    """
    Retorna vídeo transcodificado para download.
    """
    try:
        from fastapi.responses import FileResponse

        file_path = transcoding_service.get_video_path(video_id)

        if not transcoding_service.video_exists(video_id):
            raise HTTPException(status_code=404, detail="Vídeo não encontrado")

        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            filename=f"{video_id}.mp4",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro em /api/download-transcoded: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/api/transcoding-stats")
async def get_transcoding_stats():
    """
    Retorna estatísticas de uso de armazenamento de vídeos transcodificados.
    """
    try:
        stats = transcoding_service.get_storage_usage()
        return stats
    except Exception as e:
        logger.error(f"❌ Erro em /api/transcoding-stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


class ProcessToSupabaseRequest(BaseModel):
    url: str
    user_id: str
    bookmark_id: str
    quality: str = "720p"


class ProcessToSupabaseResponse(BaseModel):
    success: bool
    cloud_url: str = None
    file_size_mb: float = None
    error: str = None


@app.post("/api/process-to-supabase", response_model=ProcessToSupabaseResponse)
async def process_video_to_supabase(request: ProcessToSupabaseRequest):
    """
    Processa vídeo COMPLETO e faz upload direto para Supabase Storage.

    Fluxo:
    1. Apify extrai URL do vídeo
    2. Backend baixa vídeo
    3. FFmpeg transcodifica (H.264 Baseline)
    4. Upload direto para Supabase Storage
    5. Atualiza bookmark no Supabase
    6. Retorna apenas sucesso/falha

    VANTAGEM: Vídeo NÃO trafega para o PC - tudo servidor→servidor
    """
    import httpx
    from datetime import datetime

    try:
        logger.info(f"🚀 Processando vídeo para Supabase: {request.url}")

        # 1. Detectar plataforma e extrair URL
        platform = apify_service.detect_platform(request.url)
        logger.info(f"🎬 Plataforma: {platform}")

        if platform == Platform.INSTAGRAM:
            video_data = await apify_service.extract_video_download_url_instagram(request.url, request.quality)
        elif platform == Platform.TIKTOK:
            video_data = await apify_service.extract_video_download_url_tiktok(request.url, request.quality)
        else:
            raise ValueError(f"Plataforma não suportada: {platform}")

        download_url = video_data["download_url"]
        thumbnail_url = video_data.get("thumbnail_url")  # Apify retorna thumbnail
        logger.info(f"✅ URL extraída: {download_url[:50]}...")

        # 2. Baixar e salvar thumbnail (se disponível)
        cloud_thumbnail_url = None
        if thumbnail_url:
            try:
                logger.info(f"📸 Baixando thumbnail...")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    thumb_response = await client.get(thumbnail_url)
                    thumb_response.raise_for_status()
                    thumbnail_data = thumb_response.content

                # Upload thumbnail para Supabase Storage
                thumbnail_storage_path = f"{request.user_id}/thumbnails/{request.bookmark_id}.jpg"

                import io
                supabase_client.storage.from_('user-videos').upload(
                    thumbnail_storage_path,
                    io.BytesIO(thumbnail_data),
                    file_options={"content-type": "image/jpeg"}
                )

                # Gerar URL assinada para thumbnail
                cloud_thumbnail_url = supabase_client.storage.from_('user-videos').create_signed_url(
                    thumbnail_storage_path,
                    expires_in=31536000  # 1 ano
                )['signedURL']

                logger.info(f"✅ Thumbnail salva!")
            except Exception as thumb_error:
                logger.warning(f"⚠️  Erro ao salvar thumbnail (não crítico): {str(thumb_error)}")
                # Não falha o processo se thumbnail falhar

        # 3. Transcodificar (baixa + FFmpeg)
        logger.info(f"🎬 Baixando e transcodificando...")
        transcode_result = await transcoding_service.transcode_video(download_url)

        if not transcode_result["success"]:
            raise ValueError(f"Falha na transcodificação: {transcode_result.get('error')}")

        transcoded_path = transcode_result["file_path"]
        file_size_mb = transcode_result["file_size_mb"]

        logger.info(f"✅ Transcodificado: {file_size_mb:.2f}MB")

        # 3.5. Análise Multimodal (opcional mas recomendado)
        video_transcript = None
        visual_analysis = None
        transcript_language = None
        video_transcript_pt = None
        visual_analysis_pt = None

        if video_analysis_service.is_available():
            try:
                logger.info(f"🎤🖼️  Analisando vídeo (áudio + visual)...")
                video_analysis = await video_analysis_service.analyze_video(transcoded_path)

                if video_analysis:
                    video_transcript = video_analysis.get("transcript", "")
                    visual_analysis = video_analysis.get("visual_analysis", "")
                    transcript_language = video_analysis.get("language", "")
                    video_transcript_pt = video_analysis.get("transcript_pt")
                    visual_analysis_pt = video_analysis.get("visual_analysis_pt")

                    logger.info(f"✅ Análise multimodal concluída!")
                    logger.info(f"   - Transcrição: {len(video_transcript)} chars ({transcript_language})")
                    logger.info(f"   - Análise Visual: {len(visual_analysis)} chars")
                    if video_transcript_pt:
                        logger.info(f"   - Tradução PT (Transcrição): {len(video_transcript_pt)} chars")
                    if visual_analysis_pt:
                        logger.info(f"   - Tradução PT (Visual): {len(visual_analysis_pt)} chars")
            except Exception as analysis_error:
                # Não crítico - continua mesmo se análise falhar
                logger.warning(f"⚠️  Análise multimodal falhou (não crítico): {str(analysis_error)}")
        else:
            logger.info(f"⏭️  Análise multimodal desabilitada (OPENAI_API_KEY não configurada)")

        # 4. Upload direto para Supabase Storage
        logger.info(f"☁️  Fazendo upload para Supabase...")

        storage_path = f"{request.user_id}/{request.bookmark_id}.mp4"

        with open(transcoded_path, 'rb') as f:
            supabase_client.storage.from_('user-videos').upload(
                storage_path,
                f,
                file_options={"content-type": "video/mp4"}
            )

        # Gerar URL assinada
        cloud_url = supabase_client.storage.from_('user-videos').create_signed_url(
            storage_path,
            expires_in=31536000  # 1 ano
        )['signedURL']

        logger.info(f"✅ Upload concluído!")

        # 4. Atualizar bookmark no Supabase
        update_data = {
            'cloud_video_url': cloud_url,
            'cloud_upload_status': 'completed',
            'cloud_uploaded_at': datetime.utcnow().isoformat(),
            'cloud_file_size_bytes': int(file_size_mb * 1024 * 1024),
            'video_quality': request.quality,
        }

        # Adiciona thumbnail URL se disponível
        if cloud_thumbnail_url:
            update_data['cloud_thumbnail_url'] = cloud_thumbnail_url

        # Adiciona dados de análise multimodal se disponíveis
        if video_transcript:
            update_data['video_transcript'] = video_transcript
        if visual_analysis:
            update_data['visual_analysis'] = visual_analysis
        if transcript_language:
            update_data['transcript_language'] = transcript_language
        if video_transcript_pt:
            update_data['video_transcript_pt'] = video_transcript_pt
        if visual_analysis_pt:
            update_data['visual_analysis_pt'] = visual_analysis_pt
        if video_transcript or visual_analysis:
            update_data['analyzed_at'] = datetime.utcnow().isoformat()

        supabase_client.table('bookmarks').update(update_data).eq('id', request.bookmark_id).execute()

        logger.info(f"✅ Bookmark atualizado!")

        # 5. Limpar arquivo transcodificado
        os.unlink(transcoded_path)

        return ProcessToSupabaseResponse(
            success=True,
            cloud_url=cloud_url,
            file_size_mb=file_size_mb
        )

    except Exception as e:
        logger.error(f"❌ Erro em /api/process-to-supabase: {str(e)}")
        return ProcessToSupabaseResponse(
            success=False,
            error=str(e)
        )


# ============================================================================
# NOVO ENDPOINT: Processamento completo em background (Celery)
# ============================================================================

class ProcessBookmarkCompleteRequest(BaseModel):
    """
    Request para processamento completo de bookmark em background
    """
    bookmark_id: str
    url: str
    user_id: str
    extract_metadata: bool = True
    analyze_video: bool = True
    process_ai: bool = True
    upload_to_cloud: bool = False
    user_context: Optional[str] = None  # Contexto do usuário (peso 40% na IA)


class ProcessBookmarkCompleteResponse(BaseModel):
    """
    Response imediata com job_id
    """
    success: bool
    job_id: str = None
    bookmark_id: str = None
    estimated_time_seconds: int = None
    message: str = None
    error: str = None


@app.post("/api/process-bookmark-complete", response_model=ProcessBookmarkCompleteResponse)
async def process_bookmark_complete(
    request: ProcessBookmarkCompleteRequest,
    background_tasks: BackgroundTasks
):
    """
    **PROCESSAMENTO 100% EM BACKGROUND (FastAPI Background Tasks)**

    Phone envia requisição e desconecta - backend processa TUDO em background.

    **Fluxo:**
    1. Valida requisição
    2. Adiciona task em background (FastAPI Background Tasks)
    3. Retorna success IMEDIATAMENTE
    4. Backend processa em background:
       - Extração de metadados (Apify)
       - Análise de vídeo (Gemini Flash 2.5) - OPCIONAL
       - Processamento de IA (Claude)
       - Atualiza Supabase
    5. Phone sincroniza via Supabase Realtime

    **Parâmetros:**
    - bookmark_id: UUID do bookmark (já criado no Supabase)
    - url: URL do vídeo (YouTube/Instagram/TikTok)
    - user_id: UUID do usuário
    - extract_metadata: Extrair metadados? (padrão: True)
    - analyze_video: Analisar vídeo com Gemini? (padrão: True)
    - process_ai: Processar com Claude? (padrão: True)
    - upload_to_cloud: Upload de vídeo pra cloud? (padrão: False)
    - user_context: Contexto do usuário (opcional, peso 40% na IA)

    **Retorna:**
    - success: True/False
    - bookmark_id: UUID do bookmark
    - estimated_time_seconds: Tempo estimado (60-150s)

    **Vantagens:**
    - ✅ Phone NÃO precisa ficar aberto
    - ✅ Simples (sem Redis/Celery)
    - ✅ Processa 2-3 vídeos simultâneos
    - ✅ Phone sincroniza automaticamente via Realtime
    - ✅ Grátis (sem custo extra)
    """
    try:
        logger.info(f"🚀 Nova requisição de processamento - Bookmark: {request.bookmark_id}")

        # Validações básicas
        if not request.bookmark_id or not request.url or not request.user_id:
            return ProcessBookmarkCompleteResponse(
                success=False,
                error="bookmark_id, url e user_id são obrigatórios"
            )

        # Atualizar status inicial no Supabase: queued
        try:
            supabase_client.table('bookmarks').update({
                'processing_status': 'queued',
                'error_message': None
            }).eq('id', request.bookmark_id).execute()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao atualizar status inicial (bookmark pode não existir): {str(e)}")
            # Não bloqueia - background task vai criar/atualizar depois

        # Adicionar task em background (FastAPI Background Tasks)
        background_tasks.add_task(
            process_bookmark_background,
            bookmark_id=request.bookmark_id,
            url=request.url,
            user_id=request.user_id,
            extract_metadata=request.extract_metadata,
            analyze_video=request.analyze_video,
            process_ai=request.process_ai,
            upload_to_cloud=request.upload_to_cloud,
            user_context=request.user_context
        )

        # Estimar tempo de processamento
        estimated_time = 60  # Base: 60s
        if request.analyze_video:
            estimated_time += 60  # +60s para Gemini
        if request.upload_to_cloud:
            estimated_time += 30  # +30s para upload

        logger.info(f"✅ Background task adicionada - Bookmark: {request.bookmark_id}")

        return ProcessBookmarkCompleteResponse(
            success=True,
            job_id=request.bookmark_id,  # Usa bookmark_id como job_id (não tem job_id separado)
            bookmark_id=request.bookmark_id,
            estimated_time_seconds=estimated_time,
            message=f"Bookmark em processamento. Tempo estimado: {estimated_time}s"
        )

    except Exception as e:
        logger.error(f"❌ Erro ao enfileirar job - Bookmark: {request.bookmark_id}, Erro: {str(e)}")
        return ProcessBookmarkCompleteResponse(
            success=False,
            error=f"Erro ao enfileirar processamento: {str(e)}"
        )


# ============================================================================
# ENDPOINT DE DIAGNÓSTICO: Verificar versão do código
# ============================================================================

@app.get("/api/debug/code-version")
async def debug_code_version():
    """
    Endpoint para verificar se o código corrigido está deployado.
    Verifica se o upload duplo de thumbnail foi removido do apify_service.py
    """
    import inspect

    # Ler código-fonte do método extract_instagram_reel
    source_code = inspect.getsource(apify_service.extract_instagram_reel)

    # Verificar se tem o upload duplo (bug)
    has_bug = "storage_service.upload_thumbnail" in source_code and "extract_instagram_reel" in source_code

    # Verificar se tem o comentário da correção
    has_fix_comment = "Não fazer upload aqui - o background_processor faz depois" in source_code

    # Pegar hash do arquivo para identificar versão
    import hashlib
    code_hash = hashlib.md5(source_code.encode()).hexdigest()[:8]

    return {
        "service": "apify_service.extract_instagram_reel",
        "has_double_upload_bug": has_bug,
        "has_fix_comment": has_fix_comment,
        "code_hash": code_hash,
        "status": "FIXED" if has_fix_comment and not has_bug else "BUGGY",
        "message": "Código corrigido deployado" if has_fix_comment and not has_bug else "ATENÇÃO: Código bugado ainda em produção!",
        "snippet": source_code[400:600] if len(source_code) > 400 else source_code[:200]
    }


# ============================================================================
# IDEA CAPTURE - Processamento de ideias via áudio
# ============================================================================

async def process_idea_background(idea_id: str, audio_path: str, user_id: str):
    """
    Processa ideia em background: transcrição + análise IA + salva no Supabase.
    """
    try:
        logger.info(f"🧠 INICIANDO processamento de ideia - ID: {idea_id}")

        # 1. Atualizar status → processing
        supabase_client.table('ideas').update({
            'status': 'processing'
        }).eq('id', idea_id).execute()

        # 2. Transcrever áudio com Whisper
        logger.info(f"🎤 Transcrevendo áudio da ideia...")
        transcription = await whisper_service.transcribe_audio(audio_path, language="pt")

        if not transcription:
            raise Exception("Falha na transcrição do áudio")

        logger.info(f"✅ Transcrição: {len(transcription)} caracteres")

        # 3. Buscar projetos existentes do usuário para matching
        existing_projects = []
        try:
            projects_result = supabase_client.table('bookmarks').select('projects').eq('user_id', user_id).not_.is_('projects', 'null').execute()
            if projects_result.data:
                all_projects = set()
                for row in projects_result.data:
                    if row.get('projects'):
                        for p in row['projects']:
                            all_projects.add(p)
                # Também buscar projetos das ideas
                ideas_result = supabase_client.table('ideas').select('project').eq('user_id', user_id).not_.is_('project', 'null').execute()
                if ideas_result.data:
                    for row in ideas_result.data:
                        if row.get('project'):
                            all_projects.add(row['project'])
                existing_projects = list(all_projects)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar projetos existentes: {e}")

        # 4. Analisar com Gemini 3 Pro
        logger.info(f"🤖 Analisando ideia com Gemini 3 Pro...")

        projects_str = ", ".join(existing_projects) if existing_projects else "Nenhum projeto ainda"

        prompt = f"""Você é um assistente especializado em organizar ideias e notas de voz.

TRANSCRIÇÃO DO ÁUDIO:
"{transcription}"

PROJETOS EXISTENTES DO USUÁRIO:
{projects_str}

TAREFA:
Analise a transcrição da ideia e extraia informações estruturadas.

1. Crie um TÍTULO descritivo e conciso para a ideia (máximo 60 caracteres)
2. Escreva um RESUMO claro da ideia (2-3 frases)
3. Extraia TAGS relevantes (máximo 5, em português)
4. Sugira CATEGORIAS (1-3) entre:
   - Ideia de Produto
   - Ideia de Conteúdo
   - Ideia de Feature
   - Ideia de Negócio
   - Melhoria de Processo
   - Referência/Inspiração
   - Problema a Resolver
   - Outro
5. Identifique o PROJETO mencionado (se houver):
   - Se a pessoa mencionou um projeto específico, use o nome exato
   - Se mencionou algo similar a um projeto existente, use o existente
   - Se não mencionou projeto, retorne null
6. Identifique o TIPO da nota:
   - "idea": uma ideia ou sugestão criativa
   - "task": uma tarefa concreta a ser feita
   - "reminder": um lembrete de algo
   - "note": observação geral ou anotação

REGRAS:
- O título deve ser auto-explicativo (alguém lendo só o título deve entender a ideia)
- Tags em minúsculas, sem acentos, separadas
- Se a transcrição é confusa ou incompleta, faça o melhor possível
- Responda APENAS com JSON válido, sem markdown

FORMATO DE RESPOSTA (JSON):
{{
    "title": "Título da ideia",
    "summary": "Resumo claro da ideia em 2-3 frases.",
    "tags": ["tag1", "tag2", "tag3"],
    "categories": ["Ideia de Feature"],
    "project": "Nome do projeto" ou null,
    "note_type": "idea"
}}"""

        title = None
        summary = None
        tags = []
        categories = []
        project = None

        try:
            output = claude_service.client.run(
                claude_service.model_version,
                input={
                    "images": [],
                    "max_output_tokens": 4096,
                    "prompt": prompt,
                    "temperature": 1,
                    "thinking_level": "high",
                    "top_p": 0.95,
                    "videos": []
                }
            )

            response_text = ""
            for chunk in output:
                response_text += chunk

            # Limpar markdown code blocks
            json_text = response_text.strip()
            if json_text.startswith("```"):
                lines = json_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                json_text = '\n'.join(lines).strip()

            import json
            result = json.loads(json_text)

            title = result.get('title')
            summary = result.get('summary')
            tags = result.get('tags', [])
            categories = result.get('categories', [])
            project = result.get('project')
            note_type = result.get('note_type', 'note')

            logger.info(f"✅ IA processou: título='{title}', {len(tags)} tags, projeto={project}, tipo={note_type}")

        except Exception as e:
            logger.error(f"❌ Erro na análise IA: {str(e)}")
            # Fallback: usa transcrição como resumo
            title = transcription[:60] + ('...' if len(transcription) > 60 else '')
            summary = transcription
            note_type = 'note'

        # 5. Salvar tudo no Supabase
        update_data = {
            'status': 'completed',
            'transcription': transcription,
            'title': title,
            'summary': summary,
            'tags': tags,
            'categories': categories,
            'processed_at': 'now()',
            'error_message': None,
        }
        if project:
            update_data['project'] = project

        supabase_client.table('ideas').update(update_data).eq('id', idea_id).execute()

        logger.info(f"✅ IDEIA PROCESSADA - ID: {idea_id}, Título: {title}")

        # 6. Enviar para separador-calls (organizar em pastas locais)
        try:
            import httpx
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    "https://calls.beplus.community/api/idea",
                    json={
                        "type": "idea.processed",
                        "title": title,
                        "summary": summary,
                        "transcription": transcription,
                        "project": project,
                        "tags": tags,
                        "categories": categories,
                        "note_type": note_type,
                    },
                    timeout=10
                )
            logger.info("✅ Ideia enviada para separador-calls")
        except Exception as sc_error:
            logger.warning(f"⚠️ Falha ao enviar para separador-calls: {sc_error}")

    except Exception as e:
        logger.error(f"❌ ERRO processando ideia {idea_id}: {str(e)}", exc_info=True)
        try:
            supabase_client.table('ideas').update({
                'status': 'failed',
                'error_message': str(e)[:500],
                'processed_at': 'now()',
            }).eq('id', idea_id).execute()
        except Exception as update_error:
            logger.error(f"❌ Erro ao atualizar status failed: {str(update_error)}")
    finally:
        # Limpar arquivo temporário
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.debug(f"🗑️ Arquivo temporário removido: {audio_path}")
        except Exception:
            pass


@app.post("/api/process-idea")
async def process_idea(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    idea_id: str = Form(...),
    user_id: str = Form(...)
):
    """
    Recebe áudio de uma ideia, transcreve e analisa em background.
    Retorna imediatamente - resultado via Supabase Realtime.
    """
    try:
        logger.info(f"🎤 Recebendo áudio de ideia: {audio_file.filename}, idea_id: {idea_id}")

        # Salvar áudio temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
            content = await audio_file.read()
            tmp_file.write(content)
            temp_path = tmp_file.name

        logger.info(f"📁 Áudio salvo: {temp_path} ({len(content)} bytes)")

        # Processar em background
        background_tasks.add_task(
            process_idea_background,
            idea_id=idea_id,
            audio_path=temp_path,
            user_id=user_id,
        )

        return {
            "success": True,
            "idea_id": idea_id,
            "message": "Ideia em processamento. Acompanhe via Realtime."
        }

    except Exception as e:
        logger.error(f"❌ Erro em /api/process-idea: {str(e)}")
        return {"success": False, "error": f"Erro ao processar ideia: {str(e)}"}


@app.on_event("shutdown")
async def shutdown_event():
    await apify_service.close()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )