#!/bin/bash

echo "🔄 Reiniciando backend com APIs configuradas..."

# Ativar ambiente virtual
source venv/bin/activate

# Verificar se .env existe
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado!"
    exit 1
fi

# Verificar se as chaves foram configuradas
if grep -q "COLE_SUA_YOUTUBE_KEY_AQUI" .env; then
    echo "⚠️  YouTube API Key ainda não foi configurada!"
    echo "   Edite o arquivo .env e substitua COLE_SUA_YOUTUBE_KEY_AQUI pela sua chave"
fi

if grep -q "COLE_SEU_APIFY_TOKEN_AQUI" .env; then
    echo "⚠️  Apify Token ainda não foi configurado!"
    echo "   Edite o arquivo .env e substitua COLE_SEU_APIFY_TOKEN_AQUI pelo seu token"
fi

echo ""
echo "📊 Configuração atual:"
echo "-------------------"
grep "YOUTUBE_API_KEY\|APIFY_TOKEN" .env | sed 's/=.*$/=***HIDDEN***/'
echo ""

# Iniciar servidor
echo "🚀 Iniciando servidor..."
uvicorn main:app --reload --port 8000