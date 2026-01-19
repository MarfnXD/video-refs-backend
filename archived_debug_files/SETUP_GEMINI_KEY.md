# 🔑 Como obter GEMINI_API_KEY

Para gerar embeddings, você precisa de uma API key do Google AI Studio.

## Passo a passo:

1. **Acesse:** https://aistudio.google.com/apikey

2. **Faça login** com sua conta Google

3. **Clique em "Create API Key"**

4. **Copie a chave** (formato: `AIza...`)

5. **Adicione ao `.env` do backend:**

```bash
# Adicionar esta linha no arquivo backend/.env
GEMINI_API_KEY=AIza_sua_chave_aqui
```

## Informações importantes:

- ✅ **Grátis:** 1.500 requisições/dia
- ✅ **Embeddings:** ~$0.00001 por embedding (praticamente grátis)
- ✅ **Sem cartão de crédito necessário**

## Depois de adicionar:

Execute novamente o script:
```bash
cd backend
source venv/bin/activate
python generate_embeddings_backfill.py
```

---

**Enquanto isso, o sistema continua funcionando com a distribuição por categoria (fallback).**
