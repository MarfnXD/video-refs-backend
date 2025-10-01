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
from models import VideoMetadata
from services.apify_service import ApifyService
from services.whisper_service import whisper_service
from services.claude_service import claude_service

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


class ExtractRequest(BaseModel):
    url: str


class ExtractResponse(BaseModel):
    success: bool
    data: VideoMetadata = None
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

    Retorna:
    - VideoMetadata com todos os dados extraídos
    - Cache automático por 7 dias
    """
    try:
        if not request.url:
            raise HTTPException(status_code=400, detail="URL é obrigatória")

        metadata = await apify_service.extract_metadata(request.url)

        return ExtractResponse(
            success=True,
            data=metadata
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