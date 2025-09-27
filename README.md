# Video Refs Backend

Backend em Python/FastAPI para extração de metadados ricos de vídeos das plataformas YouTube, Instagram e TikTok.

## Recursos

- ✅ **YouTube Data API v3** - Extração oficial de metadados completos
- ✅ **Instagram/TikTok** - Web scraping via Apify
- ✅ **Cache Redis** - Performance otimizada com TTL de 7 dias
- ✅ **CORS** - Configurado para integração Flutter
- ✅ **Deploy Render.com** - HTTPS para compatibilidade Android

## API Endpoints

### POST /api/extract-metadata
Extrai metadados completos de um vídeo.

**Payload:**
```json
{
  "url": "https://youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "title": "Título do Vídeo",
    "description": "Descrição...",
    "thumbnail_url": "https://...",
    "view_count": 1000000,
    "like_count": 50000,
    "comment_count": 1000,
    "hashtags": ["#tag1", "#tag2"],
    "url": "https://...",
    "platform": "youtube"
  }
}
```

### GET /health
Health check do serviço.

## Configuração

### Variáveis de Ambiente
```bash
YOUTUBE_API_KEY=your_youtube_api_key
APIFY_API_TOKEN=your_apify_token
REDIS_URL=redis://localhost:6379
```

### Instalação Local
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Deploy

Configurado para deploy automático no Render.com via GitHub.

**Comando de Start:** `uvicorn main:app --host 0.0.0.0 --port $PORT`