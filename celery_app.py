"""
Celery App Configuration
Configuração do job queue com Redis broker
"""
from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

# Redis URL (local: redis://localhost:6379/0, produção: env var)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Criar app Celery
celery_app = Celery(
    "video_refs_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"]  # Importa tasks.py automaticamente
)

# Configurações do Celery
celery_app.conf.update(
    # Timezone
    timezone="America/Sao_Paulo",
    enable_utc=True,

    # Serialização (JSON é mais seguro que pickle)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Expiração de resultados (7 dias)
    result_expires=3600 * 24 * 7,

    # Retry policy padrão
    task_acks_late=True,  # Só marca como "feito" depois de completar
    task_reject_on_worker_lost=True,  # Se worker crashar, re-enfileira task

    # Timeout padrão (10 minutos por task)
    task_time_limit=600,
    task_soft_time_limit=540,  # Aviso 1 min antes do hard limit

    # Concorrência (quantos workers paralelos)
    # Render Free: 512MB RAM = 1 worker (evita crash por falta de memória)
    worker_concurrency=1,
    worker_prefetch_multiplier=1,  # Pega 1 task por vez (evita sobrecarga)

    # Logs
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s",

    # Beat schedule (cron jobs)
    beat_schedule={
        # Auto-sync diário às 3h da manhã
        "auto-sync-incomplete-bookmarks": {
            "task": "tasks.auto_sync_incomplete_bookmarks_task",
            "schedule": crontab(hour=3, minute=0),  # 3:00 AM todos os dias
        },
        # Cleanup de arquivos temporários a cada 6 horas
        "cleanup-temp-files": {
            "task": "tasks.cleanup_temp_files_task",
            "schedule": crontab(minute=0, hour="*/6"),  # 0:00, 6:00, 12:00, 18:00
        },
    },
)

# Eventos de lifecycle (pra monitoramento)
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup de tasks periódicas (executado ao iniciar workers)"""
    print("✅ Celery configurado com sucesso!")
    print(f"📡 Redis URL: {REDIS_URL}")
    print(f"👷 Workers: {celery_app.conf.worker_concurrency}")
