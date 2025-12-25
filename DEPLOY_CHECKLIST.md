# ✅ Checklist de Deploy - Video Refs Backend

## ✅ PRÉ-DEPLOY (COMPLETO)

- [x] Código backend completo (Celery + Workers + Gemini + Claude)
- [x] Código Flutter completo (Background Sync + Realtime + UI badges)
- [x] Migrations SQL criadas
- [x] Dockerfile configurado
- [x] docker-compose.yml para testes locais
- [x] Scripts de deploy (start-workers.sh, test-worker.sh)
- [x] Documentação completa (DEPLOY.md)
- [x] Código commitado e pushed no GitHub

## 🚀 PASSOS DE DEPLOY (A FAZER)

### 1. Redis Cloud (5 minutos)
- [ ] Acessar https://redis.com/try-free
- [ ] Criar conta (ou logar)
- [ ] Criar novo database (Free tier - 30MB)
- [ ] Copiar **Redis URL** (formato: `redis://default:password@host:port`)
- [ ] Guardar URL para próximo passo

### 2. Supabase Migration (2 minutos)
- [ ] Acessar Supabase Dashboard: https://supabase.com/dashboard/project/twwpcnyqpwznzarguzit
- [ ] Ir em **SQL Editor**
- [ ] Copiar conteúdo de `backend/migrations/add_processing_status_fields.sql`
- [ ] Colar no editor e **executar**
- [ ] Verificar que os campos foram criados: `processing_status`, `job_id`, `error_message`, etc.

### 3. Render - Opção A: Standard Plan (RECOMENDADO)
**Custo: $25/mês (API) + $0/mês (Redis grátis) = $25/mês total**

- [ ] Acessar Render Dashboard: https://dashboard.render.com
- [ ] Ir no serviço **video-refs-backend**
- [ ] Ir em **Settings** → **Instance Type**
- [ ] Mudar de **Starter** para **Standard** ($25/mo)
- [ ] Confirmar mudança
- [ ] **Adicionar variáveis de ambiente**:
  - [ ] `REDIS_URL` = (URL copiada do Redis Cloud)
  - [ ] `GEMINI_API_KEY` = (sua API key do Replicate para Gemini Flash 2.5)
  - [ ] Verificar que já existem: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`, `REPLICATE_API_TOKEN`, `APIFY_TOKEN`

- [ ] Ir em **Manual Deploy** → **Deploy latest commit**
- [ ] Aguardar deploy completar (~5-10 min)

### 4. Render - Iniciar Workers
- [ ] Abrir terminal SSH no Render (botão **Shell** no dashboard)
- [ ] Rodar comando para iniciar workers:
  ```bash
  ./start-workers.sh
  ```
- [ ] Verificar nos logs que workers iniciaram:
  ```
  [INFO] celery@worker ready.
  [INFO] celery beat started.
  ```

### 5. Verificação Pós-Deploy

#### 5.1. Testar Health Check
- [ ] Acessar no navegador: https://video-refs-backend.onrender.com/health
- [ ] Deve retornar: `{"status": "healthy"}`

#### 5.2. Testar Enfileiramento de Job
- [ ] Enviar POST request (pode usar Postman/cURL):
  ```bash
  curl -X POST https://video-refs-backend.onrender.com/api/process-bookmark-complete \
    -H "Content-Type: application/json" \
    -d '{
      "bookmark_id": "test-123",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "user_id": "test-user",
      "extract_metadata": true,
      "analyze_video": true,
      "process_ai": true,
      "upload_to_cloud": false,
      "user_context": "Test deploy"
    }'
  ```
- [ ] Deve retornar JSON com `job_id` e `estimated_time_seconds`

#### 5.3. Monitorar Logs do Worker
- [ ] No Render Shell, rodar:
  ```bash
  tail -f /var/log/celery/worker.log
  ```
- [ ] Verificar que job foi processado:
  ```
  [INFO] Task tasks.extract_metadata_task[...] succeeded
  [INFO] Task tasks.analyze_video_gemini_task[...] succeeded
  [INFO] Task tasks.process_claude_task[...] succeeded
  ```

### 6. Compilar e Instalar APK Atualizado

- [ ] No PC, ir para diretório do Flutter:
  ```bash
  cd /Users/marcoantoniorussofeioento/Documents/dev/video_refs
  ```

- [ ] Compilar APK release:
  ```bash
  flutter build apk --release
  ```

- [ ] Conectar celular via USB e verificar:
  ```bash
  adb devices
  ```

- [ ] Instalar APK:
  ```bash
  adb install -r build/app/outputs/flutter-apk/app-release.apk
  ```

### 7. Teste End-to-End no Celular

- [ ] Abrir app **Video Refs**
- [ ] Compartilhar vídeo do Instagram/YouTube para o app
- [ ] Adicionar contexto de captura: "Teste deploy backend workers"
- [ ] **FECHAR O APP** imediatamente após salvar
- [ ] Aguardar 1-2 minutos
- [ ] Reabrir app
- [ ] Verificar que bookmark aparece com:
  - [ ] Badge "Processando" (ícone engrenagem girando) OU
  - [ ] Badge "Completo" (checkmark verde) se já finalizou
  - [ ] Metadados completos (título, descrição, thumbnail)
  - [ ] Tags verdes (automáticas) geradas pela IA
  - [ ] Categorias amarelas (automáticas) geradas pela IA

- [ ] **SE DER ERRO**: Abrir Debug Screen (ícone 🐛) e verificar logs

## 📊 CUSTOS MENSAIS ESPERADOS

### Opção A: Standard Plan (Recomendado)
- Render Standard: **$25.00/mês** (always-on, workers integrados)
- Redis Cloud Free Tier: **$0.00/mês** (30MB suficiente)
- **TOTAL: ~$25/mês**

### APIs (baseado em 100 vídeos/mês):
- Apify (scraping): ~$5-10/mês
- Gemini Flash 2.5: ~$3-5/mês (30% mais barato que Whisper+GPT-4)
- Claude API: ~$2-3/mês
- **TOTAL APIs: ~$10-18/mês**

**TOTAL GERAL: ~$35-43/mês**

---

## 🆘 TROUBLESHOOTING

### Workers não iniciam
```bash
# Verificar se Redis está acessível
redis-cli -u $REDIS_URL ping
# Deve retornar: PONG

# Reiniciar workers
pkill -f celery
./start-workers.sh
```

### Jobs ficam presos em "queued"
- Verificar logs: `tail -f /var/log/celery/worker.log`
- Verificar variáveis de ambiente: `env | grep -E '(REDIS|SUPABASE|ANTHROPIC|REPLICATE|APIFY|GEMINI)'`

### APK não instala no celular
```bash
# Desinstalar versão antiga primeiro
adb uninstall com.example.video_refs

# Reinstalar
adb install build/app/outputs/flutter-apk/app-release.apk
```

### Realtime não atualiza UI
- Verificar que migration foi executada no Supabase
- Verificar logs do app (🐛 Debug Screen)
- Verificar console do navegador (se usar Web)

---

## 📖 DOCUMENTAÇÃO COMPLETA

Para detalhes técnicos completos, consulte:
- **backend/DEPLOY.md** - Guia completo de deploy
- **CLAUDE.md** - Arquitetura e fluxo do sistema
- **backend/README.md** - Documentação da API

---

**Status:** ✅ Pronto para deploy!
**Última verificação:** 25/12/2024
