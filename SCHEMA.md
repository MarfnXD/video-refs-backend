# SCHEMA DA TABELA BOOKMARKS

**IMPORTANTE**: Este arquivo é gerado automaticamente lendo todas as migrations.
Sempre consulte este arquivo ANTES de adicionar campos em `background_processor.py`!

## ✅ COLUNAS QUE EXISTEM NO SUPABASE


### Básicas

- ✅ `id` - UUID PRIMARY KEY
- ✅ `user_id` - UUID REFERENCES users
- ✅ `url` - TEXT
- ✅ `created_at` - TIMESTAMP WITH TIME ZONE
- ✅ `updated_at` - TIMESTAMP WITH TIME ZONE

### Metadados

- ✅ `title` - TEXT
- ✅ `platform` - TEXT
- ✅ `metadata` - JSONB

### Processamento IA

- ✅ `auto_description` - TEXT
- ✅ `auto_tags` - TEXT[]
- ✅ `auto_categories` - TEXT[]
- ❌ `confidence` - **NÃO ENCONTRADO** (verificar migrations)
- ✅ `relevance_score` - FLOAT

### Análise Multimodal

- ✅ `video_transcript` - TEXT
- ✅ `visual_analysis` - TEXT
- ✅ `transcript_language` - VARCHAR(10)
- ✅ `analyzed_at` - TIMESTAMP

### Tradução

- ❌ `title_translated_pt` - **NÃO ENCONTRADO** (verificar migrations)
- ❌ `description_translated_pt` - **NÃO ENCONTRADO** (verificar migrations)
- ❌ `transcript_translated_pt` - **NÃO ENCONTRADO** (verificar migrations)

### Contexto do Usuário

- ✅ `user_context_raw` - TEXT
- ✅ `user_context_processed` - TEXT

### Download Local

- ✅ `local_video_path` - TEXT
- ✅ `downloaded_at` - TIMESTAMP WITH TIME ZONE
- ✅ `video_file_size_bytes` - BIGINT
- ✅ `video_quality` - TEXT
- ❌ `frames_generated_at` - **NÃO ENCONTRADO** (verificar migrations)

### Cloud Sync

- ✅ `cloud_video_url` - TEXT
- ✅ `cloud_upload_status` - TEXT
- ✅ `cloud_uploaded_at` - TIMESTAMPTZ
- ✅ `cloud_file_size_bytes` - BIGINT

### Embeddings

- ✅ `embedding` - vector(1536)

### Background Processing

- ✅ `processing_status` - TEXT
- ✅ `job_id` - TEXT
- ✅ `error_message` - TEXT
- ✅ `processing_started_at` - TIMESTAMP WITH TIME ZONE
- ✅ `processing_completed_at` - TIMESTAMP WITH TIME ZONE

### ⚠️ Outras Colunas (não categorizadas)

- `ai_processed` - BOOLEAN
- `categories` - TEXT[]
- `cloud_thumbnail_url` - TEXT
- `direct_video_url` - TEXT
- `filtered_comments` - JSONB
- `original_title` - TEXT
- `projects` - TEXT[]
- `published_at` - TIMESTAMP WITH TIME ZONE
- `tags` - TEXT[]
- `thumbnail` - TEXT
- `video_transcript_pt` - TEXT
- `visual_analysis_pt` - TEXT


## 📊 TOTAL: 44 colunas

## 📋 LISTA SIMPLES (para validação rápida)

```python
BOOKMARKS_COLUMNS = [
    'ai_processed',
    'analyzed_at',
    'auto_categories',
    'auto_description',
    'auto_tags',
    'categories',
    'cloud_file_size_bytes',
    'cloud_thumbnail_url',
    'cloud_upload_status',
    'cloud_uploaded_at',
    'cloud_video_url',
    'created_at',
    'direct_video_url',
    'downloaded_at',
    'embedding',
    'error_message',
    'filtered_comments',
    'id',
    'job_id',
    'local_video_path',
    'metadata',
    'original_title',
    'platform',
    'processing_completed_at',
    'processing_started_at',
    'processing_status',
    'projects',
    'published_at',
    'relevance_score',
    'tags',
    'thumbnail',
    'title',
    'transcript_language',
    'updated_at',
    'url',
    'user_context_processed',
    'user_context_raw',
    'user_id',
    'video_file_size_bytes',
    'video_quality',
    'video_transcript',
    'video_transcript_pt',
    'visual_analysis',
    'visual_analysis_pt',
]
```
