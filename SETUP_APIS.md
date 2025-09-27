# 🔑 Configuração das APIs - Passo a Passo

## 1️⃣ YouTube Data API v3 (GRÁTIS)

### Passo 1: Acessar Google Cloud Console
1. Abra: https://console.cloud.google.com/
2. Faça login com sua conta Google

### Passo 2: Criar Projeto (ou usar existente)
1. Clique no dropdown do projeto (topo da página)
2. Clique em "Novo Projeto"
3. Nome: `video-refs` (ou qualquer nome)
4. Clique em "Criar"

### Passo 3: Ativar YouTube Data API
1. No menu lateral, vá para **"APIs e serviços" > "Biblioteca"**
2. Pesquise por: `YouTube Data API v3`
3. Clique no resultado
4. Clique em **"ATIVAR"**

### Passo 4: Criar Credencial
1. Após ativar, clique em **"CRIAR CREDENCIAIS"**
2. Selecione:
   - Qual API? **YouTube Data API v3**
   - De onde você chamará? **Servidor web (Node.js, Python, etc)**
   - Que dados? **Dados públicos**
3. Clique em **"Que credenciais preciso?"**
4. **COPIE A API KEY** que aparecerá

### Passo 5: (Opcional) Restringir a Key
1. Clique em "Restringir chave"
2. Em "Restrições de API", selecione "Restringir chave"
3. Marque apenas "YouTube Data API v3"
4. Salvar

**SUA YOUTUBE API KEY:** `AIza...` (cole aqui após criar)

---

## 2️⃣ Apify Token (GRÁTIS - $5 créditos/mês)

### Passo 1: Criar Conta
1. Abra: https://console.apify.com/sign-up
2. Crie conta com Google ou email
3. Confirme email se necessário

### Passo 2: Obter Token
1. Após login, clique no seu avatar (canto superior direito)
2. Vá para **"Settings"**
3. Na aba lateral, clique em **"Integrations"**
4. Em "Personal API tokens", você verá seu token
5. **COPIE O TOKEN** (formato: `apify_api_...`)

### Passo 3: Verificar Créditos
1. No dashboard, você verá seus créditos gratuitos ($5/mês)
2. Isso é suficiente para ~500 extrações/mês

**SEU APIFY TOKEN:** `apify_api_...` (cole aqui após criar)

---

## 3️⃣ Redis (Opcional - para cache)

### Opção A: Usar Redis Local (Mac)
```bash
# Instalar Redis
brew install redis

# Iniciar Redis
brew services start redis

# URL: redis://localhost:6379
```

### Opção B: Redis Cloud (GRÁTIS - 30MB)
1. Criar conta em: https://redis.com/try-free/
2. Criar database gratuito
3. Copiar connection string

---

## 4️⃣ Configurar Backend

### Criar arquivo .env
```bash
cd backend/
cp .env.example .env
```

### Editar .env com suas chaves:
```env
# YouTube Data API v3
YOUTUBE_API_KEY=AIza... # Cole sua key aqui

# Apify
APIFY_TOKEN=apify_api_... # Cole seu token aqui

# Redis (opcional)
REDIS_URL=redis://localhost:6379

# Server
PORT=8000
ENVIRONMENT=development
```

---

## 5️⃣ Testar APIs

### Reiniciar Backend
```bash
# Parar backend atual (Ctrl+C)
# Reiniciar com novas variáveis
source venv/bin/activate
uvicorn main:app --reload
```

### Teste 1: YouTube
```bash
curl -X POST http://localhost:8000/api/extract-metadata \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

Resposta esperada:
```json
{
  "success": true,
  "data": {
    "title": "Rick Astley - Never Gonna Give You Up",
    "views": 1000000000,
    "likes": 12345678,
    ...
  }
}
```

### Teste 2: Instagram
```bash
curl -X POST http://localhost:8000/api/extract-metadata \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/C1234567890/"}'
```

### Teste 3: TikTok
```bash
curl -X POST http://localhost:8000/api/extract-metadata \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@user/video/7123456789012345678"}'
```

---

## ✅ Checklist Final

- [ ] YouTube API Key obtida e configurada
- [ ] Apify Token obtido e configurado
- [ ] Arquivo .env criado com as chaves
- [ ] Backend reiniciado
- [ ] Teste com YouTube funcionando
- [ ] Teste com Instagram funcionando
- [ ] Teste com TikTok funcionando

---

## 🚨 Troubleshooting

### Erro: "quota exceeded"
- YouTube API tem limite de 10.000 unidades/dia
- Cada request consome ~3 unidades
- Solução: Aguardar reset diário ou criar novo projeto

### Erro: "Apify actor not found"
- Verificar se os actors estão disponíveis:
  - Instagram: `apify/instagram-scraper`
  - TikTok: `clockworks/tiktok-scraper`

### Erro: "Connection refused"
- Verificar se backend está rodando
- Verificar se está na porta 8000
- No Flutter, usar 10.0.2.2 para emulador Android

---

## 🎯 URLs de Teste

### YouTube
- https://www.youtube.com/watch?v=dQw4w9WgXcQ (Rick Roll)
- https://www.youtube.com/watch?v=9bZkp7q19f0 (Gangnam Style)
- https://youtu.be/kJQP7kiw5Fk (Despacito)

### Instagram Reels (precisam ser reais)
- Abra Instagram no navegador
- Procure por qualquer reel
- Copie a URL

### TikTok
- https://www.tiktok.com/@cristiano/video/7236968416559836442
- Ou qualquer vídeo público do TikTok