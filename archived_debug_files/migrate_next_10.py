"""
Script para migrar os próximos 10 vídeos não migrados do CSV
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
    """Detecta plataforma"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'tiktok.com' in url or 'vm.tiktok.com' in url:
        return 'tiktok'
    return 'other'

def generate_temporary_title(url, platform):
    """Gera título temporário"""
    titles = {
        'youtube': 'YouTube Video (processando...)',
        'instagram': 'Instagram Reel (processando...)',
        'tiktok': 'TikTok Video (processando...)',
    }
    return titles.get(platform, 'Video (processando...)')

print("="*80)
print("MIGRAÇÃO - PRÓXIMOS 10 VÍDEOS")
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
        if row['migrado'] == 'NÃO' and len(urls_to_migrate) < 10:
            url = row['URL']
            if ('/reel/' in url or '/share/reel/' in url):
                urls_to_migrate.append({
                    'id': row['ID'],
                    'url': url
                })

print(f"✓ Encontradas {len(urls_to_migrate)} URLs para migrar")
print()

# Processar cada URL
print("📥 Processando bookmarks...")
print()

created_bookmarks = []
failed_bookmarks = []

for idx, item in enumerate(urls_to_migrate, 1):
    url = item['url']
    csv_id = item['id']
    
    print(f"[{idx}/{len(urls_to_migrate)}] ID {csv_id}")
    print(f"  URL: {url[:60]}...")
    
    try:
        # 1. Criar bookmark no Supabase
        platform = detect_platform(url)
        now = datetime.utcnow()
        
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
            raise Exception('Supabase retornou null ao criar bookmark')
        
        bookmark_id = result.data[0]['id']
        print(f"  ✅ Bookmark criado: {bookmark_id[:8]}...")
        
        # 2. Chamar endpoint backend
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
                raise Exception(f'Backend retornou status {response.status_code}: {response.text[:100]}')
            
            backend_data = response.json()
            
            if backend_data.get('success') != True:
                raise Exception(f'Backend falhou: {backend_data.get("error", "erro desconhecido")}')
            
            job_id = backend_data.get('job_id')
            estimated_time = backend_data.get('estimated_time_seconds', 90)
            
            print(f"  ✅ Enfileirado: job_id={job_id[:8]}...")
            print(f"  ⏱️  Tempo estimado: {estimated_time}s")
            
            created_bookmarks.append({
                'csv_id': csv_id,
                'url': url,
                'bookmark_id': bookmark_id,
                'job_id': job_id,
                'estimated_time': estimated_time
            })
        
        except requests.exceptions.Timeout:
            print(f"  ⏱️  Timeout 30s (backend processa mesmo assim)")
            created_bookmarks.append({
                'csv_id': csv_id,
                'url': url,
                'bookmark_id': bookmark_id,
                'job_id': None,
                'timeout': True
            })
    
    except Exception as e:
        print(f"  ❌ Erro: {str(e)[:100]}")
        failed_bookmarks.append({
            'csv_id': csv_id,
            'url': url,
            'error': str(e)[:100]
        })
    
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
    with open('migrate_10_bookmark_ids.txt', 'w') as f:
        for bm in created_bookmarks:
            f.write(f"{bm['bookmark_id']}\n")
    print(f"💾 IDs salvos em: migrate_10_bookmark_ids.txt")
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
    for fail in failed_bookmarks[:5]:
        print(f"   ID {fail['csv_id']}: {fail['error'][:60]}")
    print()

print("✨ Migração finalizada!")
print("   Backend está processando os vídeos em background.")
print("   Acompanhe via Supabase dashboard ou app Flutter.")
