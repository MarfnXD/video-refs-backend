#!/usr/bin/env python3
"""
Script de Verificação Pré-Deploy
Checa se todos os arquivos e configurações estão prontos para deploy no Render.
"""

import os
import sys
from pathlib import Path

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_file(filepath: str, description: str) -> bool:
    """Verifica se arquivo existe."""
    if os.path.exists(filepath):
        print(f"{GREEN}✅ {description}{RESET}")
        return True
    else:
        print(f"{RED}❌ {description} - FALTANDO: {filepath}{RESET}")
        return False

def check_env_vars() -> bool:
    """Verifica variáveis de ambiente críticas."""
    print(f"\n{BLUE}📋 VARIÁVEIS DE AMBIENTE{RESET}")

    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "ANTHROPIC_API_KEY",
        "REPLICATE_API_TOKEN",
        "APIFY_TOKEN",
        "REDIS_URL",
    ]

    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f"{GREEN}✅ {var} configurado{RESET}")
        else:
            print(f"{YELLOW}⚠️  {var} NÃO configurado (precisa adicionar no Render){RESET}")
            missing.append(var)

    return len(missing) == 0

def main():
    print(f"{BLUE}{'='*60}")
    print("🔍 VERIFICAÇÃO PRÉ-DEPLOY - Video Refs Backend")
    print(f"{'='*60}{RESET}\n")

    all_good = True

    # 1. Arquivos principais
    print(f"{BLUE}📁 ARQUIVOS PRINCIPAIS{RESET}")
    all_good &= check_file("main.py", "main.py (FastAPI server)")
    all_good &= check_file("celery_app.py", "celery_app.py (Celery config)")
    all_good &= check_file("tasks.py", "tasks.py (Workers)")
    all_good &= check_file("requirements.txt", "requirements.txt")
    all_good &= check_file("Dockerfile", "Dockerfile")
    all_good &= check_file("render.yaml", "render.yaml")

    # 2. Services
    print(f"\n{BLUE}🔧 SERVICES{RESET}")
    all_good &= check_file("services/gemini_service.py", "GeminiService")
    all_good &= check_file("services/claude_service.py", "ClaudeService")
    all_good &= check_file("services/apify_service.py", "ApifyService")
    all_good &= check_file("services/whisper_service.py", "WhisperService")
    all_good &= check_file("services/transcoding_service.py", "TranscodingService")

    # 3. Migrations
    print(f"\n{BLUE}🗄️  MIGRATIONS{RESET}")
    all_good &= check_file("migrations/add_processing_status_fields.sql", "Migration: processing_status")

    # 4. Docker & Dev tools
    print(f"\n{BLUE}🐳 DOCKER & DEV{RESET}")
    all_good &= check_file("docker-compose.yml", "docker-compose.yml")
    all_good &= check_file("start-workers.sh", "start-workers.sh")
    all_good &= check_file("start-docker.sh", "start-docker.sh")
    all_good &= check_file("test-worker.sh", "test-worker.sh")

    # 5. Documentação
    print(f"\n{BLUE}📚 DOCUMENTAÇÃO{RESET}")
    all_good &= check_file("DEPLOY.md", "DEPLOY.md (guia completo)")

    # 6. Variáveis de ambiente (só checa, não bloqueia)
    env_ok = check_env_vars()

    # 7. Verificar se scripts são executáveis
    print(f"\n{BLUE}🔐 PERMISSÕES DE EXECUÇÃO{RESET}")
    scripts = ["start-workers.sh", "start-docker.sh", "test-worker.sh"]
    for script in scripts:
        if os.path.exists(script):
            is_executable = os.access(script, os.X_OK)
            if is_executable:
                print(f"{GREEN}✅ {script} é executável{RESET}")
            else:
                print(f"{YELLOW}⚠️  {script} não é executável (rode: chmod +x {script}){RESET}")

    # 8. Resumo final
    print(f"\n{BLUE}{'='*60}")
    print("📊 RESUMO")
    print(f"{'='*60}{RESET}\n")

    if all_good:
        print(f"{GREEN}✅ TODOS OS ARQUIVOS NECESSÁRIOS ESTÃO PRESENTES!{RESET}\n")

        print(f"{BLUE}🚀 PRÓXIMOS PASSOS PARA DEPLOY:{RESET}")
        print(f"{YELLOW}1. Criar Redis Cloud database (https://redis.com/try-free)")
        print(f"2. Atualizar Render para Standard Plan ou adicionar Worker services")
        print(f"3. Configurar variáveis de ambiente no Render Dashboard")
        print(f"4. Executar migration SQL no Supabase")
        print(f"5. Fazer deploy e monitorar logs")
        print(f"\n📖 Guia completo: backend/DEPLOY.md{RESET}\n")

        return 0
    else:
        print(f"{RED}❌ FALTAM ARQUIVOS! Verifique os erros acima.{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
