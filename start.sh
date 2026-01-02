#!/bin/bash

# Script de inicialização para Render
# Inicia FastAPI + Celery Worker + Celery Beat em paralelo

echo "🚀 Iniciando todos os serviços..."

# Iniciar Celery Worker em background
# RENDER FREE: 512MB RAM = 2 workers (teste de performance)
echo "⚙️ Iniciando Celery Worker (2 workers - teste de performance)..."
celery -A celery_app worker --loglevel=info --concurrency=2 &

# Iniciar Celery Beat em background (cron jobs)
echo "⏰ Iniciando Celery Beat..."
celery -A celery_app beat --loglevel=info &

# Aguardar 3 segundos para workers iniciarem
sleep 3

# Iniciar FastAPI (foreground - processo principal)
echo "🌐 Iniciando FastAPI..."
uvicorn main:app --host 0.0.0.0 --port $PORT
