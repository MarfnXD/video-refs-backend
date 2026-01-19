# Correção: Bug de Double Upload de Thumbnail

**Data:** 02/01/2026
**Commit:** `a90cc5a`
**Status:** ✅ Correção implementada | ⏳ Aguardando deploy completo no Render

---

## 🐛 Problema Identificado

### Sintoma
- Alguns bookmarks (ex: Red Bull `eefc288c-655a-4abb-b1c7-ac79460d3cf6`) tinham thumbnails quebradas no app
- Campo `metadata.thumbnail_url` estava corrompido com URLs do Supabase Storage
- Deveria conter apenas URLs originais do Instagram CDN

### Causa Raiz
**Double upload de thumbnail** em 2 lugares diferentes:

1. **`services/apify_service.py` (linhas 416-424)** - ❌ INCORRETO
   - Fazia upload da thumbnail para Supabase Storage
   - Quando bem-sucedido, sobrescrevia `final_thumbnail_url` com URL do Supabase
   - Esta URL do Supabase era salva em `metadata.thumbnail_url` (deveria ser Instagram CDN)

2. **`background_processor.py` (linhas 245-265)** - ✅ CORRETO
   - Upload correto da thumbnail
   - Salva em `cloud_thumbnail_url` (campo da tabela)

3. **Modelo `VideoMetadata`** - ❌ DESNECESSÁRIO
   - Tinha campo `cloud_thumbnail_url` (linha 29 de `models.py`)
   - `background_processor.py` copiava esse campo (linha 86)
   - Campo não deveria existir no modelo de resposta do Apify

### Fluxo Bugado

```
Instagram URL → Apify → VideoMetadata
                           ↓
                  thumbnail_url (Instagram CDN)
                           ↓
                  Upload para Supabase ❌ (apify_service.py)
                           ↓
                  SOBRESCREVE thumbnail_url com URL do Supabase
                           ↓
                  background_processor.py recebe URL corrompida
                           ↓
                  metadata.thumbnail_url = URL do Supabase (ERRADO!)
```

---

## ✅ Correção Implementada

### Arquivos Modificados

#### 1. `services/apify_service.py`

**ANTES (linhas 410-427):**
```python
caption = data.get("caption", "Instagram Reel")
hashtags = re.findall(r"#\w+", caption)
temp_thumbnail_url = data.get("displayUrl", "")
final_thumbnail_url = temp_thumbnail_url
try:
    if temp_thumbnail_url:
        permanent_thumbnail = await storage_service.upload_thumbnail(temp_thumbnail_url, url)
        if permanent_thumbnail:
            final_thumbnail_url = permanent_thumbnail  # ← BUG: Sobrescreve com Supabase URL
except Exception:
    pass
metadata = VideoMetadata(
    ...
    thumbnail_url=final_thumbnail_url,  # ← URL corrompida
    ...
)
```

**DEPOIS:**
```python
caption = data.get("caption", "Instagram Reel")
hashtags = re.findall(r"#\w+", caption)
# Thumbnail original do Instagram (CDN)
# IMPORTANTE: Não fazer upload aqui - o background_processor faz depois
thumbnail_url = data.get("displayUrl", "")
metadata = VideoMetadata(
    ...
    thumbnail_url=thumbnail_url,  # ← URL original preservada
    ...
)
```

#### 2. `models.py`

**ANTES (linha 29):**
```python
class VideoMetadata(BaseModel):
    thumbnail_url: Optional[str] = None
    cloud_thumbnail_url: Optional[str] = None  # ← Campo desnecessário
    duration: Optional[str] = None
```

**DEPOIS:**
```python
class VideoMetadata(BaseModel):
    thumbnail_url: Optional[str] = None  # URL original da plataforma (Instagram/TikTok/YouTube CDN)
    duration: Optional[str] = None
```

#### 3. `background_processor.py`

**ANTES (linha 86):**
```python
metadata = {
    'title': video_metadata.title,
    'description': video_metadata.description,
    'thumbnail_url': video_metadata.thumbnail_url,
    'cloud_thumbnail_url': video_metadata.cloud_thumbnail_url,  # ← Copiava campo que não existe mais
    'duration': video_metadata.duration,
    ...
}
```

**DEPOIS:**
```python
metadata = {
    'title': video_metadata.title,
    'description': video_metadata.description,
    'thumbnail_url': video_metadata.thumbnail_url,  # ← Preserva Instagram CDN
    'duration': video_metadata.duration,
    ...
}
```

### Fluxo Corrigido

```
Instagram URL → Apify → VideoMetadata
                           ↓
                  thumbnail_url (Instagram CDN) ✅
                           ↓
                  background_processor.py
                           ↓
                  metadata.thumbnail_url = Instagram CDN ✅
                           ↓
                  Upload para Supabase (background_processor)
                           ↓
                  cloud_thumbnail_url (campo da tabela) = Supabase URL ✅
```

---

## 📊 Resultado Esperado

Após a correção, novos bookmarks devem ter:

1. **`metadata.thumbnail_url`** → URL original do Instagram CDN
   - Exemplo: `https://scontent.cdninstagram.com/v/t51.2885-15/...`

2. **`cloud_thumbnail_url`** (campo da tabela) → URL do Supabase Storage
   - Exemplo: `https://twwpcnyqpwznzarguzit.supabase.co/storage/v1/object/public/thumbnails/...`

3. **Upload acontece apenas uma vez** em `background_processor.py` (linhas 245-265)

---

## 🧪 Teste Criado

### `test_single_bookmark_fix.py`

Script para validar a correção:
1. Cria novo bookmark no Supabase
2. Enfileira processamento completo via API do Render
3. Aguarda processamento (max 3 minutos)
4. Valida 5 campos críticos:
   - ✅ `cloud_thumbnail_url` → Supabase Storage
   - ✅ `metadata.thumbnail_url` → Instagram CDN original
   - ✅ `cloud_video_url` → Supabase Storage
   - ✅ `video_transcript` e `visual_analysis` → Gemini
   - ✅ `smart_title` → Gerado

**Bookmark de teste criado:** `887430ad-9355-4d65-9fa8-cd67ef6cf9e0`
**Status atual:** `processing` (travado - worker não processou)

---

## ⚠️ Próximos Passos

1. **Verificar deploy no Render:**
   - Acessar dashboard do Render
   - Confirmar que deploy do commit `a90cc5a` foi concluído com sucesso
   - Verificar logs do Celery worker

2. **Reprocessar bookmark de teste:**
   - Se worker estiver funcionando, aguardar finalização
   - Validar se campos estão corretos conforme esperado

3. **Se teste passar:**
   - Continuar migração dos 50 Instagram URLs restantes
   - Monitorar qualidade das thumbnails

4. **Se worker não estiver funcionando:**
   - Verificar configuração do Redis no Render
   - Verificar variáveis de ambiente (REDIS_URL, CELERY_BROKER_URL)
   - Reiniciar workers se necessário

---

## 📝 Commit

```
fix: Corrigir bug de double upload de thumbnail

PROBLEMA:
- metadata.thumbnail_url estava sendo corrompida com URLs do Supabase
- Deveria conter apenas URLs originais do Instagram CDN
- Alguns bookmarks (ex: Red Bull) tinham thumbnails quebradas

CAUSA:
- apify_service.py fazia upload da thumbnail (linhas 416-424)
- Ao ter sucesso, sobrescrevia thumbnail_url com URL do Supabase
- background_processor.py também fazia upload (correto)
- Modelo VideoMetadata tinha campo cloud_thumbnail_url desnecessário
- background_processor.py copiava esse campo (linha 86)

CORREÇÃO:
1. Removido upload de thumbnail do apify_service.py
2. Removido campo cloud_thumbnail_url do modelo VideoMetadata
3. Removido cópia de cloud_thumbnail_url no background_processor.py linha 86

RESULTADO:
- metadata.thumbnail_url agora preserva URL original do Instagram CDN
- cloud_thumbnail_url (campo da tabela) recebe URL do Supabase Storage
- Upload de thumbnail acontece apenas uma vez (background_processor)
```

---

## 🔍 Investigação Anterior

Scripts criados durante investigação:
- `investigate_apify_response.py` - Verificou bookmarks com `metadata.thumbnail_url` corrompida
- `debug_red_bull.py` - Análise detalhada do bookmark Red Bull
- `fix_missing_thumbnails.py` - Tentativa de corrigir thumbnails (não usado)
- `test_random_thumbnails.py` - Validou que 100% das thumbnails existentes funcionam

**Descoberta:** Bug afetava apenas alguns bookmarks (quando primeiro upload tinha sucesso). Maioria funcionava porque primeiro upload falhava (HTTP 403) e mantinha URL do Instagram, que era uploadada corretamente depois.
