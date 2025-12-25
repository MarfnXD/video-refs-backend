#!/bin/bash
# Script para iniciar tudo com Docker Compose
# Uso: ./start-docker.sh

echo "🐳 Iniciando Video Refs com Docker Compose..."
echo ""

# Verificar se Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando"
    echo "   Inicie o Docker Desktop e tente novamente"
    exit 1
fi

echo "✅ Docker detectado"
echo ""

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "   Copie .env.example para .env e configure as variáveis"
    exit 1
fi

echo "✅ Arquivo .env encontrado"
echo ""

# Build e start dos containers
echo "🔨 Building containers..."
docker-compose build

echo ""
echo "🚀 Iniciando serviços..."
docker-compose up -d

echo ""
echo "⏳ Aguardando serviços iniciarem..."
sleep 5

echo ""
echo "✅ Todos os serviços iniciados!"
echo ""
echo "📊 Containers rodando:"
docker-compose ps

echo ""
echo "🌐 Acesso:"
echo "   - Flower (monitoramento): http://localhost:5555"
echo "   - Redis: localhost:6379"
echo ""
echo "📝 Logs:"
echo "   - Ver todos: docker-compose logs -f"
echo "   - Ver worker: docker-compose logs -f celery_worker"
echo "   - Ver beat: docker-compose logs -f celery_beat"
echo ""
echo "🛑 Para parar tudo:"
echo "   docker-compose down"
echo ""
