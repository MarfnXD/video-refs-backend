#!/usr/bin/env python3
"""
Script de teste para envio em leva de vídeos via API.
Testa o pipeline completo: Metadata → Gemini 2.5 Flash → Gemini 3.0 Pro

Usage:
    python test_batch_processing.py
"""
import os
import csv
import time
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
from datetime import datetime

# Cores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BACKEND_URL = "https://video-refs-backend.onrender.com"  # Produção
# BACKEND_URL = "http://localhost:8000"  # Para teste local

# Inicializar Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_or_create_test_user():
    """Pega user_id válido de bookmark existente ou usa Marco (padrão)"""
    try:
        # Usar user_id do Marco (padrão)
        user_id = "0ed9bb40-0041-4dca-9649-256cb418f403"
        print(f"{Colors.OKGREEN}✓ Usando user_id do Marco: {user_id}{Colors.ENDC}")
        return user_id

    except Exception as e:
        print(f"{Colors.FAIL}❌ Erro: {e}{Colors.ENDC}")
        return None

def create_bookmark_in_db(user_id: str, url: str):
    """Cria bookmark no Supabase database"""
    try:
        bookmark_id = str(uuid.uuid4())

        data = {
            'id': bookmark_id,
            'user_id': user_id,
            'url': url,
            'processing_status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
        }

        result = supabase.table('bookmarks').insert(data).execute()

        if result.data:
            print(f"{Colors.OKCYAN}  ✓ Bookmark criado no DB: {bookmark_id[:8]}...{Colors.ENDC}")
            return bookmark_id
        else:
            print(f"{Colors.FAIL}  ❌ Falha ao criar bookmark no DB{Colors.ENDC}")
            return None

    except Exception as e:
        print(f"{Colors.FAIL}  ❌ Erro ao criar bookmark: {e}{Colors.ENDC}")
        return None

def call_processing_api(bookmark_id: str, url: str, user_id: str):
    """Chama API de processamento"""
    try:
        payload = {
            "bookmark_id": bookmark_id,
            "url": url,
            "user_id": user_id,
            "extract_metadata": True,
            "analyze_video": True,
            "process_ai": True,
            "upload_to_cloud": True,  # ✅ FAZER UPLOAD ANTES - URLs do Instagram expiram rápido!
        }

        response = requests.post(
            f"{BACKEND_URL}/api/process-bookmark-complete",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id', 'N/A')
            estimated_time = data.get('estimated_time_seconds', 0)
            print(f"{Colors.OKGREEN}  ✓ Job enfileirado: {job_id[:8]}... (tempo estimado: {estimated_time}s){Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}  ❌ API retornou erro {response.status_code}: {response.text[:100]}{Colors.ENDC}")
            return False

    except requests.exceptions.Timeout:
        print(f"{Colors.FAIL}  ❌ Timeout ao chamar API (backend pode estar dormindo - aguarde 30s){Colors.ENDC}")
        return False
    except Exception as e:
        print(f"{Colors.FAIL}  ❌ Erro ao chamar API: {e}{Colors.ENDC}")
        return False

def monitor_bookmark_status(bookmark_id: str, max_wait_seconds: int = 300):
    """Monitora status do bookmark até completar ou falhar"""
    start_time = time.time()
    last_status = None

    while (time.time() - start_time) < max_wait_seconds:
        try:
            result = supabase.table('bookmarks').select('processing_status, error_message').eq('id', bookmark_id).execute()

            if result.data and len(result.data) > 0:
                status = result.data[0]['processing_status']
                error_msg = result.data[0].get('error_message', '')

                # Mostrar mudança de status
                if status != last_status:
                    elapsed = int(time.time() - start_time)

                    if status == 'queued':
                        print(f"{Colors.OKBLUE}  ⏳ Status: Enfileirado ({elapsed}s){Colors.ENDC}")
                    elif status == 'processing':
                        print(f"{Colors.WARNING}  ⚙️  Status: Processando ({elapsed}s){Colors.ENDC}")
                    elif status == 'completed':
                        print(f"{Colors.OKGREEN}  ✅ Status: COMPLETO ({elapsed}s){Colors.ENDC}")
                        return True
                    elif status == 'failed':
                        print(f"{Colors.FAIL}  ❌ Status: FALHOU ({elapsed}s) - {error_msg[:60]}{Colors.ENDC}")
                        return False

                    last_status = status

            time.sleep(3)  # Aguardar 3s antes de consultar novamente

        except Exception as e:
            print(f"{Colors.FAIL}  ❌ Erro ao monitorar status: {e}{Colors.ENDC}")
            return False

    print(f"{Colors.WARNING}  ⏱️  Timeout (>{max_wait_seconds}s) - processamento pode estar lento{Colors.ENDC}")
    return False

def process_video_batch(csv_path: str, num_videos: int = 5):
    """Processa leva de vídeos do CSV"""

    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"🧪 TESTE DE PROCESSAMENTO EM LEVA")
    print(f"{'='*70}{Colors.ENDC}\n")

    # 1. Validar user_id
    print(f"{Colors.BOLD}1️⃣ Validando usuário...{Colors.ENDC}")
    user_id = get_or_create_test_user()
    if not user_id:
        print(f"\n{Colors.FAIL}❌ Impossível continuar sem user_id válido{Colors.ENDC}")
        return

    # 2. Ler CSV
    print(f"\n{Colors.BOLD}2️⃣ Lendo CSV...{Colors.ENDC}")
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            urls = [row['URL'] for row in reader][:num_videos]

        print(f"{Colors.OKGREEN}✓ {len(urls)} vídeos carregados{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}❌ Erro ao ler CSV: {e}{Colors.ENDC}")
        return

    # 3. Processar cada vídeo
    print(f"\n{Colors.BOLD}3️⃣ Processando {len(urls)} vídeos...{Colors.ENDC}\n")

    results = {
        'success': 0,
        'failed': 0,
        'enqueued': 0,
    }

    for idx, url in enumerate(urls, 1):
        print(f"{Colors.BOLD}{'─'*70}")
        print(f"📹 Vídeo {idx}/{len(urls)}: {url[:60]}...")
        print(f"{'─'*70}{Colors.ENDC}")

        # Criar bookmark no DB
        bookmark_id = create_bookmark_in_db(user_id, url)
        if not bookmark_id:
            results['failed'] += 1
            continue

        # Enfileirar processamento
        success = call_processing_api(bookmark_id, url, user_id)
        if not success:
            results['failed'] += 1
            continue

        results['enqueued'] += 1

        # Monitorar status (opcional - comentar se quiser apenas enfileirar sem esperar)
        if monitor_bookmark_status(bookmark_id, max_wait_seconds=180):
            results['success'] += 1
        else:
            results['failed'] += 1

        print()  # Linha em branco entre vídeos

        # Aguardar 2s antes do próximo (evitar rate limiting)
        if idx < len(urls):
            time.sleep(2)

    # 4. Resumo final
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"📊 RESUMO DO TESTE")
    print(f"{'='*70}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}✅ Processados com sucesso: {results['success']}{Colors.ENDC}")
    print(f"{Colors.WARNING}⏳ Enfileirados: {results['enqueued']}{Colors.ENDC}")
    print(f"{Colors.FAIL}❌ Falharam: {results['failed']}{Colors.ENDC}")
    print()

    # 5. Instruções para monitorar no Render
    print(f"{Colors.BOLD}📍 Para acompanhar os logs no Render:{Colors.ENDC}")
    print(f"1. Acesse: https://dashboard.render.com")
    print(f"2. Services → video-refs-backend-worker")
    print(f"3. Logs → buscar por [PIPELINE] ou [METADATA] ou [GEMINI]")
    print()

if __name__ == "__main__":
    import sys

    # Pegar CSV do argumento ou usar padrão
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "instagram_urls_simplified_20251226_103701.csv"
    num_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 999  # Processar todos por padrão

    # Verificar se arquivo existe
    if not os.path.exists(csv_file):
        print(f"{Colors.FAIL}❌ Arquivo não encontrado: {csv_file}{Colors.ENDC}")
        exit(1)

    # Processar vídeos
    process_video_batch(csv_file, num_videos=num_videos)
