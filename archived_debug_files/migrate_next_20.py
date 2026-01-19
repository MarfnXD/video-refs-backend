"""
Script para migrar os próximos 20 vídeos não migrados do CSV
"""
import os
import csv
import requests
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import time

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'
CSV_PATH = 'instagram_urls_migrated_20251226_214730.csv'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def detect_platform(url):
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'tiktok.com' in url or 'vm.tiktok.com' in url:
        return 'tiktok'
    return 'other'

def generate_temporary_title(url, platform):
    titles = {
        'youtube': 'YouTube Video (processando...)',
        'instagram': 'Instagram Reel (processando...)',
        'tiktok': 'TikTok Video (processando...)',
    }
    return titles.get(platform, 'Video (processando...)')

print("="*80)
print("MIGRAÇÃO - PRÓXIMOS 20 VÍDEOS")
print("="*80)
print()

# Ler CSV
print("📄 Lendo CSV...")
urls_to_migrate = []
csv_rows = []

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_rows.append(row)
        if row['migrado'] == 'NÃO' and len(urls_to_migrate) < 20:
            url = row['URL']
            if ('/reel/' in url or '/share/reel/' in url):
                urls_to_migrate.append({
                    'id': row['ID'],
                    'url': url
                })

print(f"✓ Encontradas {len(urls_to_migrate)} URLs para migrar")
print()

# Processar
print("📥 Processando bookmarks...")
print()

created_bookmarks = []
failed_bookmarks = []

for idx, item in enumerate(urls_to_migrate, 1):
    url = item['url']
    csv_id = item['id']
    
    print(f"[{idx}/{len(urls_to_migrate)}] ID {csv_id}: {url[:50]}...")
    
    try:
        # 1. Criar bookmark
        platform = detect_platform(url)
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        bookmark_data = {
            'url': url,
            'title': generate_temporary_title(url, platform),
            'platform': platform.lower(),
            'user_id': USER_ID,
            'created_at': now.isoformat(),
            'processing_status': 'queued',
        }
        
        result = supabase.table('bookmarks').insert(bookmark_data).execute()
        
        if not result.data:
            raise Exception('Supabase retornou null')
        
        bookmark_id = result.data[0]['id']
        print(f"  ✅ Criado: {bookmark_id[:8]}...")
        
        # 2. Enfileirar
        request_body = {
            'bookmark_id': bookmark_id,
            'url': url,
            'user_id': USER_ID,
            'extract_metadata': True,
            'analyze_video': True,
            'process_ai': True,
            'upload_to_cloud': True,
            'user_context': None,
        }
        
        try:
            response = requests.post(
                f'{BACKEND_URL}/api/process-bookmark-complete',
                json=request_body,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f'Backend: {response.status_code}')
            
            backend_data = response.json()
            
            if not backend_data.get('success'):
                raise Exception(f'Backend falhou: {backend_data.get("error", "?")}')
            
            job_id = backend_data.get('job_id')
            estimated_time = backend_data.get('estimated_time_seconds', 90)
            
            print(f"  ✅ Enfileirado: {job_id[:8] if job_id else 'N/A'}... ({estimated_time}s)")
            
            created_bookmarks.append({
                'csv_id': csv_id,
                'url': url,
                'bookmark_id': bookmark_id,
                'job_id': job_id,
                'estimated_time': estimated_time
            })
        
        except requests.exceptions.Timeout:
            print(f"  ⏱️  Timeout (backend processa mesmo assim)")
            created_bookmarks.append({
                'csv_id': csv_id,
                'url': url,
                'bookmark_id': bookmark_id,
                'job_id': None,
                'timeout': True
            })
    
    except Exception as e:
        error_msg = str(e)[:100]
        print(f"  ❌ Erro: {error_msg}")
        failed_bookmarks.append({
            'csv_id': csv_id,
            'url': url,
            'error': error_msg
        })
    
    # Pausa a cada 5 para não sobrecarregar
    if idx % 5 == 0 and idx < len(urls_to_migrate):
        print(f"  ⏸️  Pausa 3s...")
        time.sleep(3)
    print()

# Atualizar CSV
print("📝 Atualizando CSV...")
migrated_ids = {bm['csv_id'] for bm in created_bookmarks}

with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
    writer.writeheader()
    
    for row in csv_rows:
        if row['ID'] in migrated_ids:
            row['migrado'] = 'SIM'
            row['data_migracao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow(row)

print(f"✓ CSV atualizado")
print()

# Salvar IDs
if created_bookmarks:
    with open('migrate_20_bookmark_ids.txt', 'w') as f:
        for bm in created_bookmarks:
            f.write(f"{bm['bookmark_id']}\n")
    print(f"💾 IDs salvos: migrate_20_bookmark_ids.txt")
    print()

# Resumo
print("="*80)
print("✅ MIGRAÇÃO CONCLUÍDA")
print("="*80)
print()
print(f"📊 RESUMO:")
print(f"   Criados: {len(created_bookmarks)}")
print(f"   Falhas: {len(failed_bookmarks)}")
print(f"   Timeouts: {sum(1 for bm in created_bookmarks if bm.get('timeout'))}")
print()

if failed_bookmarks:
    print("⚠️  FALHAS:")
    for fail in failed_bookmarks[:10]:
        print(f"   ID {fail['csv_id']}: {fail['error'][:60]}")
    print()

total_time = sum(bm.get('estimated_time', 0) for bm in created_bookmarks)
print(f"⏱️  Tempo estimado: {total_time}s (~{total_time//60}min)")
print()
print("✨ Processamento em andamento no Render!")
