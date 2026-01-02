#!/bin/bash

# Script de inicialização para Render
# Inicia FastAPI + Celery Worker + Celery Beat em paralelo

echo "🚀 Iniciando todos os serviços..."

# FORÇAR concurrency=2 (alguma env var oculta do Render seta 4)
export CELERYD_CONCURRENCY=2

# Iniciar Celery Worker em background
# Concurrency controlado via CELERYD_CONCURRENCY=2
echo "⚙️ Iniciando Celery Worker (CELERYD_CONCURRENCY=2)..."
celery -A celery_app worker --loglevel=info &

# Iniciar Celery Beat em background (cron jobs)
echo "⏰ Iniciando Celery Beat..."
celery -A celery_app beat --loglevel=info &

# Aguardar 3 segundos para workers iniciarem
sleep 3

# Iniciar FastAPI (foreground - processo principal)
echo "🌐 Iniciando FastAPI..."
uvicorn main:app --host 0.0.0.0 --port $PORT
