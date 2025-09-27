from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from models import VideoMetadata
from services.apify_service import ApifyService

load_dotenv()

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