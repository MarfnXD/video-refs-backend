"""
Migrar próximos 20 vídeos não-migrados do CSV
Batch 2 - após sucesso dos primeiros 15
"""
import os
import csv
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'
CSV_FILE = 'instagram_urls_migrated_20251226_214730.csv'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def detect_platform(url):
    if 'instagram.com' in url:
        return 'Instagram'
    elif 'tiktok.com' in url:
        return 'TikTok'
    return 'Other'

def generate_temporary_title(url, platform):
    return f"{platform} Reel (processando...)"

print("="*80)
print("MIGRAÇÃO BATCH 2 - PRÓXIMOS 20 VÍDEOS")
print("="*80)
print()

# Ler CSV e pegar próximos 20 não-migrados
urls_to_migrate = []
all_rows = []

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    all_rows = list(reader)

for row in all_rows:
    if row['migrado'] == 'NÃO':
        urls_to_migrate.append(row)
        if len(urls_to_migrate) >= 20:
            break

print(f"📋 {len(urls_to_migrate)} vídeos selecionados para migração")
print()

results = []
bookmark_ids = []

for idx, row in enumerate(urls_to_migrate, 1):
    url = row['URL']
    csv_id = row['ID']

    print(f"[{idx}/20] Migrando ID {csv_id}...")
    print(f"        URL: {url[:60]}...")

    # 1. Criar bookmark
    platform = detect_platform(url)
    now = datetime.now(timezone.utc)

    bookmark_data = {
        'url': url,
        'title': generate_temporary_title(url, platform),
        'platform': platform.lower(),
        'user_id': USER_ID,
        'created_at': now.isoformat(),
        'processing_status': 'queued',
    }

    try:
        result = supabase.table('bookmarks').insert(bookmark_data).execute()
        bookmark_id = result.data[0]['id']
        bookmark_ids.append(bookmark_id)

        print(f"        ✅ Bookmark criado: {bookmark_id[:8]}...")

        # 2. Chamar backend
        try:
            response = requests.post(
                f'{BACKEND_URL}/api/process-bookmark-complete',
                json={
                    'bookmark_id': bookmark_id,
                    'url': url,
                    'user_id': USER_ID,
                    'extract_metadata': True,
                    'analyze_video': True,
                    'process_ai': True,
                    'upload_to_cloud': True,
                    'user_context': None,
                },
                timeout=30
            )

            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data.get('job_id', 'N/A')[:8]
                est_time = job_data.get('estimated_time_seconds', 0)
                print(f"        🚀 Enfileirado: job {job_id}... (~{est_time}s)")

                # Atualizar CSV
                row['migrado'] = 'SIM'
                row['data_migracao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                results.append({'csv_id': csv_id, 'bookmark_id': bookmark_id, 'success': True})
            else:
                print(f"        ❌ Erro HTTP: {response.status_code}")
                results.append({'csv_id': csv_id, 'bookmark_id': bookmark_id, 'success': False})

        except requests.exceptions.Timeout:
            print(f"        ⏱️  Timeout (processa em background)")
            row['migrado'] = 'SIM'
            row['data_migracao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            results.append({'csv_id': csv_id, 'bookmark_id': bookmark_id, 'success': True, 'timeout': True})

        except Exception as e:
            print(f"        ❌ Erro: {str(e)[:50]}")
            results.append({'csv_id': csv_id, 'bookmark_id': bookmark_id, 'success': False})

    except Exception as e:
        print(f"        ❌ Erro ao criar bookmark: {str(e)[:50]}")
        results.append({'csv_id': csv_id, 'bookmark_id': None, 'success': False})

    print()

# Atualizar CSV
with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
    writer.writeheader()
    writer.writerows(all_rows)

# Salvar IDs dos bookmarks
with open('migrate_20_batch2_bookmark_ids.txt', 'w') as f:
    for bid in bookmark_ids:
        f.write(f"{bid}\n")

# Resumo
print("="*80)
print("📊 RESUMO")
print("="*80)
success_count = sum(1 for r in results if r['success'])
print(f"✅ Migrados com sucesso: {success_count}/20")
print(f"❌ Falhas: {20 - success_count}")
print()
print(f"📝 IDs salvos em: migrate_20_batch2_bookmark_ids.txt")
print(f"📝 CSV atualizado: {CSV_FILE}")
print()

if success_count > 0:
    total_time = success_count * 150  # ~2.5min por vídeo com 2 workers
    print(f"⏱️  Tempo estimado: ~{total_time//60}min")
    print(f"👷 2 workers processando em paralelo")
