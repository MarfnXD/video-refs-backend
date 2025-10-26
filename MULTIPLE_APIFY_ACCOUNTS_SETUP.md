# 🚀 Setup: Múltiplas Contas Apify (Ninja Mode)

## 📊 Por que isso funciona?

- **Cada conta** = 5.000 créditos/mês grátis (~33 vídeos)
- **3 contas** = 15.000 créditos/mês (~100 vídeos) 🎉
- **Paralelismo 15x** (5 por conta)
- **Tempo**: 900 vídeos em ~1.5-2 horas (vs 7-8h)

---

## 📝 Passo a Passo

### 1. Criar Contas Apify (5 minutos)

Crie 2-3 contas em https://apify.com:

```
Conta 1: seu.email+apify1@gmail.com
Conta 2: seu.email+apify2@gmail.com
Conta 3: seu.email+apify3@gmail.com
```

> 💡 **Dica**: Gmail ignora tudo após `+`, então 1 email = infinitas contas!

### 2. Pegar API Tokens

Para cada conta:

1. Login em https://console.apify.com
2. **Settings** → **Integrations** → **API Tokens**
3. Copiar o token (ex: `apify_api_XYZ123...`)

### 3. Configurar no Render

**Dashboard Render:**

1. Acesse https://dashboard.render.com
2. Selecione o serviço **video-refs-backend**
3. **Environment** → Editar `APIFY_TOKEN`
4. **Cole os 3 tokens separados por vírgula:**

```bash
APIFY_TOKEN=apify_api_ABC123...,apify_api_DEF456...,apify_api_GHI789...
```

5. **Save Changes**
6. Deploy automático vai acontecer (~2 min)

### 4. Verificar Funcionamento

Faça uma requisição de teste:

```bash
curl https://video-refs-backend.onrender.com/api/extract-metadata \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/..."}'
```

Nos logs do Render você verá:

```
🔄 Usando Apify token #1/3
🔄 Usando Apify token #2/3
🔄 Usando Apify token #3/3
🔄 Usando Apify token #1/3  <- Rotação reinicia
```

---

## 🎯 Como Usar

### Opção 1: Script Python Paralelo (RECOMENDADO)

```bash
cd backend

# Instalar dependências
pip install aiohttp tqdm supabase

# Rodar download paralelo (usa todas as contas automaticamente)
python bulk_download_parallel.py \
  --user-id SEU_USER_ID \
  --parallel 15 \
  --quality 720p
```

**Resultado:**
- Usa 15 downloads simultâneos (5 por conta Apify)
- Rotaciona automaticamente entre as contas
- Progress bar em tempo real
- ~1.5-2 horas para 900 vídeos

### Opção 2: App Flutter (auto-download)

O app já usa rotação automática! Basta ativar auto-download no Admin.

---

## 💰 Monitorar Créditos

**Para cada conta:**

1. Login em https://console.apify.com
2. **Billing** → **Usage**
3. Ver créditos restantes

**Quando acabar conta 1:**
- Script automaticamente usa conta 2
- Sem interrupção! 🎉

---

## ⚠️ Limites e Recomendações

### Limites por Conta Gratuita:
- **5.000 créditos/mês**
- **~150 créditos por vídeo Instagram**
- **= ~33 vídeos/mês por conta**

### Recomendações:
- **Use 3 contas** (~100 vídeos/mês grátis)
- **Paralelismo 5 por conta** (15 total)
- **Delay 2s entre requests** (já configurado no script)

### Se Precisar de Mais:
- Crie mais contas (emails +apify4, +apify5, etc)
- Ou compre créditos ($50 = ~300 vídeos)

---

## 🐛 Troubleshooting

### Erro: "Nenhum APIFY_TOKEN configurado"
- Verifique se salvou a variável no Render
- Tokens devem estar separados por vírgula

### Erro: "Quota exceeded"
- Conta atual esgotou créditos
- Script automaticamente muda para próxima conta
- Se TODAS esgotaram: crie nova conta ou aguarde reset mensal

### Downloads muito lentos
- Verifique paralelismo (recomendado: 15 com 3 contas)
- Backend Render pode estar "dormindo" (primeira request demora)

---

## 📊 Exemplo de Uso Real

**Cenário:** 900 vídeos Instagram para baixar

```bash
# 3 contas Apify (100 vídeos grátis)
python bulk_download_parallel.py --user-id XXX --parallel 15 --limit 100

# Tempo: ~30-40 minutos
# Custo: $0

# Depois, criar mais 3 contas:
# Conta 4, 5, 6 (mais 100 vídeos grátis)

# Repetir até baixar os 900 vídeos
# Custo total: $0 (só tempo de criar ~9 contas)
```

**Alternativa paga:**
```bash
# Comprar $50 em créditos Apify
# Baixar 900 vídeos de uma vez
# Tempo: ~2 horas
# Custo: $50
```

---

## ✅ Vantagens dessa Estratégia

1. **100% Grátis** (com paciência para criar contas)
2. **Velocidade 15x** vs download sequencial
3. **Sem bloqueios** (Apify tem proteção profissional)
4. **Escalável** (crie quantas contas quiser)
5. **Zero configuração** no app (funciona automaticamente)

---

## 🎉 Resumo

✅ Backend modificado para rotação automática
✅ Script Python pronto para paralelismo
✅ 3 contas = ~100 vídeos grátis/mês
✅ ~1.5-2h para 900 vídeos (vs 7-8h)
✅ Zero bloqueios (Apify cuida)

**Bora baixar esses 900 vídeos!** 🚀
