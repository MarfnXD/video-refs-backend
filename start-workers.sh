#!/bin/bash
# Script para iniciar Celery workers localmente (sem Docker)
# Uso: ./start-workers.sh

echo "🚀 Iniciando Celery Workers + Beat + Flower..."
echo ""

# Verificar se Redis está rodando
if ! nc -z localhost 6379 2>/dev/null; then
    echo "❌ Redis não está rodando em localhost:6379"
    echo "   Inicie o Redis com: redis-server"
    echo "   Ou use Docker: docker-compose up redis -d"
    exit 1
fi

echo "✅ Redis detectado em localhost:6379"
echo ""

# Ativar venv se existir
if [ -d "venv" ]; then
    echo "📦 Ativando venv..."
    source venv/bin/activate
fi

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "   Copie .env.example para .env e configure as variáveis"
    exit 1
fi

echo "✅ Arquivo .env encontrado"
echo ""

# Criar diretórios temporários se não existirem
mkdir -p /tmp/celery_logs

# Iniciar Celery Worker em background
echo "👷 Iniciando Celery Worker (4 workers paralelos)..."
celery -A celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --logfile=/tmp/celery_logs/worker.log \
    --detach

sleep 2

# Iniciar Celery Beat em background (cron jobs)
echo "⏰ Iniciando Celery Beat (agendador de tasks)..."
celery -A celery_app beat \
    --loglevel=info \
    --logfile=/tmp/celery_logs/beat.log \
    --detach

sleep 2

# Iniciar Flower (UI de monitoramento)
echo "🌸 Iniciando Flower (UI de monitoramento)..."
echo "   Acesse: http://localhost:5555"
celery -A celery_app flower \
    --port=5555 \
    --logfile=/tmp/celery_logs/flower.log \
    --detach

sleep 2

echo ""
echo "✅ Todos os serviços iniciados!"
echo ""
echo "📊 Status:"
echo "   - Workers: 4 workers paralelos"
echo "   - Beat: Rodando (auto-sync às 3h da manhã)"
echo "   - Flower: http://localhost:5555"
echo ""
echo "📝 Logs:"
echo "   - Worker: /tmp/celery_logs/worker.log"
echo "   - Beat: /tmp/celery_logs/beat.log"
echo "   - Flower: /tmp/celery_logs/flower.log"
echo ""
echo "🛑 Para parar tudo:"
echo "   pkill -f 'celery.*worker'"
echo "   pkill -f 'celery.*beat'"
echo "   pkill -f 'celery.*flower'"
echo ""
