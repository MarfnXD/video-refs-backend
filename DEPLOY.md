# 🚀 Guia de Deploy - Video Refs Backend

## 📋 Índice
1. [Pré-requisitos](#pré-requisitos)
2. [Deploy Render (Produção)](#deploy-render-produção)
3. [Setup Redis Cloud](#setup-redis-cloud)
4. [Variáveis de Ambiente](#variáveis-de-ambiente)
5. [Executar Migration Supabase](#executar-migration-supabase)
6. [Monitoramento](#monitoramento)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Pré-requisitos

- Conta no [Render](https://render.com)
- Conta no [Redis Cloud](https://redis.com/try-free) (ou Upstash)
- Conta no [Supabase](https://supabase.com)
- Tokens de API:
  - Replicate API (Gemini + Claude)
  - Apify Tokens (múltiplos recomendado)
  - YouTube API (opcional)

---

## 🌐 Deploy Render (Produção)

### Passo 1: Migrar para Render Standard Plan

1. **Acesse o dashboard Render**: https://dashboard.render.com
2. **Selecione o serviço `video-refs-backend`**
3. **Em Settings > Instance Type**:
   - Mude de `Starter ($7/mês)` para `Standard ($25/mês)`
   - **Motivo**: Standard Plan não "dorme" (sempre ativo)
   - CPU: 1 vCPU
   - RAM: 2 GB
   - **IMPORTANTE**: Workers Celery precisam rodar 24/7

4. **Salvar e aguardar restart**

---

### Passo 2: Criar 3 Serviços no Render

Você precisa criar **3 serviços separados** (todos usando o mesmo repositório):

#### **Serviço 1: FastAPI (main.py)**
- **Type**: Web Service
- **Name**: `video-refs-api`
- **Environment**: Python 3.11
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Instance Type**: Standard ($25/mês)
- **Health Check Path**: `/health`

#### **Serviço 2: Celery Worker**
- **Type**: Background Worker
- **Name**: `video-refs-worker`
- **Environment**: Python 3.11
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `celery -A celery_app worker --loglevel=info --concurrency=4`
- **Instance Type**: Standard ($25/mês)
- **⚠️ IMPORTANTE**: Background Worker (não Web Service!)

#### **Serviço 3: Celery Beat** (Cron Jobs)
- **Type**: Background Worker
- **Name**: `video-refs-beat`
- **Environment**: Python 3.11
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `celery -A celery_app beat --loglevel=info`
- **Instance Type**: Starter ($7/mês) - Beat não precisa de muito recurso
- **⚠️ IMPORTANTE**: Background Worker (não Web Service!)

#### **Serviço 4 (Opcional): Flower** (UI de Monitoramento)
- **Type**: Web Service
- **Name**: `video-refs-flower`
- **Environment**: Python 3.11
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `celery -A celery_app flower --port=$PORT`
- **Instance Type**: Starter ($7/mês)
- **Acesso**: https://video-refs-flower.onrender.com

**💰 Custo Total Render: ~$64/mês** (API + Worker Standard + Beat Starter + Flower opcional)

---

## ☁️ Setup Redis Cloud

### Opção A: Redis Cloud (Recomendado)

1. **Acesse**: https://redis.com/try-free
2. **Criar Free Plan**:
   - 30 MB storage (suficiente para queue)
   - Uptime 99.99%
   - Grátis para sempre

3. **Criar Database**:
   - Name: `video-refs-queue`
   - Cloud: AWS
   - Region: `us-east-1` (perto do Render)

4. **Copiar Connection String**:
   ```
   redis://default:<password>@<host>:<port>
   ```

5. **Adicionar `REDIS_URL` nas env vars dos 3 serviços Render**

### Opção B: Upstash (Alternativa)

1. **Acesse**: https://upstash.com
2. **Criar database Redis**:
   - Region: US East
   - Type: Pay as you go

3. **Copiar REST URL** (Upstash tem REST API também)

**💰 Custo Redis: GRÁTIS** (30 MB free tier)

---

## 🔐 Variáveis de Ambiente

### Configurar em TODOS os 3 serviços Render:

```bash
# Supabase
SUPABASE_URL=https://twwpcnyqpwznzarguzit.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Redis (CRÍTICO - mesma URL nos 3 serviços)
REDIS_URL=redis://default:password@redis-12345.c1.us-east-1.cloud.redislabs.com:12345

# Replicate API (Gemini + Claude + Whisper)
REPLICATE_API_TOKEN=r8_...

# Apify (múltiplos tokens recomendado)
APIFY_TOKEN=apify_api_...
APIFY_TOKEN_2=apify_api_...
APIFY_TOKEN_3=apify_api_...

# YouTube API (opcional)
YOUTUBE_API_KEY=AIza...

# OpenAI (se usar análise multimodal antiga - pode remover depois)
OPENAI_API_KEY=sk-proj-...

# Gemini Model Version (Replicate)
GEMINI_MODEL_VERSION=google-deepmind/gemini-2.0-flash-exp:...
```

### ⚠️ IMPORTANTE:
- **REDIS_URL deve ser IDÊNTICA** nos 3 serviços (API + Worker + Beat)
- Se REDIS_URL estiver errada, workers não pegam jobs da fila
- Teste com: `redis-cli -u $REDIS_URL ping` (deve retornar `PONG`)

---

## 🗄️ Executar Migration Supabase

### Método 1: Via Supabase Dashboard (Recomendado)

1. **Acesse**: https://supabase.com/dashboard
2. **Projeto**: `twwpcnyqpwznzarguzit`
3. **SQL Editor** (menu lateral)
4. **New Query**
5. **Copiar conteúdo de**: `backend/migrations/add_processing_status_fields.sql`
6. **Run** (executar)
7. **Verificar**: Tabela `bookmarks` deve ter colunas `processing_status`, `job_id`, `error_message`

### Método 2: Via Python Script (Render)

Conectar via SSH no worker e rodar:

```bash
cd /opt/render/project/src
python3 run_migration.py migrations/add_processing_status_fields.sql
```

---

## 📊 Monitoramento

### Flower (UI de Monitoramento)

Acesse: **https://video-refs-flower.onrender.com**

- **Tasks**: Veja jobs em execução, completados, falhados
- **Workers**: Status de cada worker (online/offline)
- **Monitor**: Gráficos de throughput, latência
- **Broker**: Tamanho da fila Redis

### Logs Render

1. **Acesse cada serviço**:
   - https://dashboard.render.com/web/video-refs-api
   - https://dashboard.render.com/background/video-refs-worker
   - https://dashboard.render.com/background/video-refs-beat

2. **Logs → Live Logs** (atualização em tempo real)

### Comandos Úteis

```bash
# Ver status dos workers (Flower API)
curl https://video-refs-flower.onrender.com/api/workers

# Ver task específica
curl https://video-refs-flower.onrender.com/api/task/{task_id}

# Ver tamanho da fila Redis
redis-cli -u $REDIS_URL LLEN celery

# Limpar fila (CUIDADO - apaga todos os jobs)
redis-cli -u $REDIS_URL FLUSHDB
```

---

## 🔧 Troubleshooting

### Problema: Workers não pegam jobs da fila

**Sintoma**: Job fica "queued" mas nunca "processing"

**Soluções**:
1. **Verificar REDIS_URL**:
   ```bash
   # No worker Render, testar conexão
   redis-cli -u $REDIS_URL ping
   # Deve retornar: PONG
   ```

2. **Verificar se worker está rodando**:
   - Acessar Flower: https://video-refs-flower.onrender.com
   - Em "Workers" deve mostrar 1 worker online

3. **Restart do worker**:
   - Dashboard Render → video-refs-worker → Manual Deploy

---

### Problema: Auto-sync não roda às 3h da manhã

**Sintoma**: Bookmarks incompletos não são processados automaticamente

**Soluções**:
1. **Verificar se Beat está rodando**:
   - Dashboard Render → video-refs-beat → Logs
   - Deve mostrar: `Scheduler: Sending due task...`

2. **Forçar execução manual**:
   ```bash
   # Conectar no worker e executar
   python3 -c "from tasks import auto_sync_incomplete_bookmarks_task; auto_sync_incomplete_bookmarks_task.apply_async()"
   ```

3. **Verificar timezone**:
   - Celery Beat usa timezone `America/Sao_Paulo`
   - Se quiser UTC, editar `celery_app.py` linha 28

---

### Problema: Cold Start demora 30-60s

**Sintoma**: Primeira requisição após inatividade demora muito

**Solução**:
- ✅ **JÁ RESOLVIDO** ao migrar para Standard Plan
- Standard Plan **não dorme** (sempre ativo)
- Starter Plan dormia após 15min inatividade

---

### Problema: Gemini Flash 2.5 não disponível no Replicate

**Sintoma**: Erro "Model not found" ao analisar vídeo

**Soluções**:
1. **Verificar versão do modelo**:
   - Acessar: https://replicate.com/google-deepmind
   - Procurar modelo Gemini Flash 2.5
   - Copiar versão exata (hash SHA256)

2. **Atualizar env var**:
   ```bash
   GEMINI_MODEL_VERSION=google-deepmind/gemini-2.0-flash-exp:<hash>
   ```

3. **Fallback**: Se Gemini não disponível, sistema usa Whisper + GPT-4 Vision (método antigo)

---

### Problema: Custo de API muito alto

**Sintoma**: Conta Replicate/Apify/OpenAI com gasto excessivo

**Otimizações**:
1. **Desabilitar análise de vídeo por padrão**:
   - Em `main.py` endpoint `/api/process-bookmark-complete`
   - Mudar `analyze_video: bool = True` para `analyze_video: bool = False`

2. **Reduzir workers paralelos**:
   - Menos workers = menos jobs simultâneos = menos custos de API
   - Em `celery_app.py` mudar `worker_concurrency=4` para `worker_concurrency=2`

3. **Aumentar cache de metadados**:
   - Apify cache atual: 7 dias
   - Aumentar para 30 dias (economiza scraping)

---

## 📈 Custos Estimados (Produção)

| Serviço | Plano | Custo/Mês |
|---------|-------|-----------|
| **Render API** | Standard | $25 |
| **Render Worker** | Standard | $25 |
| **Render Beat** | Starter | $7 |
| **Render Flower** (opcional) | Starter | $7 |
| **Redis Cloud** | Free Tier | $0 |
| **Replicate** | Pay-as-you-go | ~$20-50 (depende do volume) |
| **Apify** | Free Tier | $0 (até limite) |
| **TOTAL** | | **~$84-114/mês** |

**Otimizações para reduzir custo:**
- Remover Flower (monitorar via logs)
- Usar apenas 2 tokens Apify (em vez de 4)
- Desabilitar análise Gemini por padrão (só quando usuário pedir)

---

## ✅ Checklist de Deploy

- [ ] Render Standard Plan configurado (API + Worker)
- [ ] Redis Cloud database criada
- [ ] REDIS_URL configurada nos 3 serviços
- [ ] Todas as env vars configuradas
- [ ] Migration Supabase executada
- [ ] 3 serviços rodando (API + Worker + Beat)
- [ ] Flower acessível (opcional)
- [ ] Teste manual: enviar bookmark → processar em background
- [ ] Auto-sync testado (forçar execução manual)
- [ ] Logs sem erros críticos

---

## 🎯 Teste de Produção

Execute este teste completo após deploy:

```bash
# 1. Criar bookmark no Supabase via API
curl -X POST https://video-refs-backend.onrender.com/api/process-bookmark-complete \
  -H "Content-Type: application/json" \
  -d '{
    "bookmark_id": "test-123",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "user_id": "user-test-456",
    "extract_metadata": true,
    "analyze_video": false,
    "process_ai": true,
    "upload_to_cloud": false
  }'

# Deve retornar: {"success": true, "job_id": "...", "estimated_time_seconds": 90}

# 2. Monitorar em Flower
# Acesse: https://video-refs-flower.onrender.com
# Procure task com job_id retornado

# 3. Aguardar ~90 segundos

# 4. Verificar no Supabase
# SELECT * FROM bookmarks WHERE id = 'test-123';
# Deve ter: title, metadata, auto_tags, auto_categories, processing_status='completed'
```

---

**🎉 Deploy Completo! Backend rodando 24/7 em produção.**
