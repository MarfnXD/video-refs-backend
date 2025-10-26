from dotenv import load_dotenv
import os

# IMPORTANTE: Carregar .env ANTES de importar os serviços
load_dotenv()

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
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
from supabase import create_client, Client

# Configurar logging
logging.basicConfig(level=logging.INFO)
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


class ProcessMetadataAutoResponse(BaseModel):
    success: bool
    auto_description: Optional[str] = None
    auto_tags: Optional[List[str]] = None
    auto_categories: Optional[List[str]] = None
    confidence: Optional[str] = None
    relevance_score: Optional[float] = None
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

        # Processar metadados com Claude
        logger.info("🤖 Processando metadados automaticamente...")
        result = await claude_service.process_metadata_auto(
            title=request.title,
            description=request.description or "",
            hashtags=request.hashtags or [],
            top_comments=request.top_comments or []
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
            relevance_score=result.get("relevance_score", 0.5)
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