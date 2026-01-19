"""
Reprocessar os 10 vídeos stuck em 'processing'
Quando worker crashou, tasks ficaram stuck no Redis
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ler IDs dos 15 vídeos
with open('migrate_20_bookmark_ids.txt', 'r') as f:
    bookmark_ids = [line.strip() for line in f if line.strip()]

print("="*80)
print("REPROCESSAR VÍDEOS STUCK")
print("="*80)
print()

stuck_count = 0
results = []

for idx, bookmark_id in enumerate(bookmark_ids, 1):
    # Buscar status do bookmark
    result = supabase.table('bookmarks').select('url, title, processing_status').eq('id', bookmark_id).execute()

    if not result.data:
        continue

    bm = result.data[0]
    status = bm['processing_status']
    title = bm['title'][:50]
    url = bm['url']

    # Só reprocessar se stuck em 'processing'
    if status != 'processing':
        print(f"[{idx:2d}] ⏭️  {status:12s} {title}... (skip)")
        continue

    stuck_count += 1
    print(f"[{idx:2d}] 🔄 {title}...")

    # Reprocessar
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/process-bookmark-complete',
            json={
                'bookmark_id': bookmark_id,
                'user_id': USER_ID,
                'url': url,
                'upload_to_cloud': True,
                'extract_metadata': True,
                'analyze_video': True,
                'process_ai': True,
                'user_context': None,
                'manual_tags': [],
                'manual_categories': []
            },
            timeout=30
        )

        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data.get('job_id', 'N/A')[:8]
            print(f"     ✅ Reenfileirado: {job_id}...")
            results.append({'bookmark_id': bookmark_id, 'success': True})
        else:
            print(f"     ❌ Erro: HTTP {response.status_code}")
            results.append({'bookmark_id': bookmark_id, 'success': False})

    except requests.exceptions.Timeout:
        print(f"     ⏱️  Timeout (backend processa mesmo assim)")
        results.append({'bookmark_id': bookmark_id, 'success': True, 'timeout': True})

    except Exception as e:
        print(f"     ❌ Erro: {str(e)[:60]}")
        results.append({'bookmark_id': bookmark_id, 'success': False})

    print()

# Resumo
print("="*80)
print("📊 RESUMO")
print("="*80)
success_count = sum(1 for r in results if r['success'])
print(f"🔄 Vídeos stuck encontrados: {stuck_count}")
print(f"✅ Reenfileirados: {success_count}")
print(f"❌ Falhas: {len(results) - success_count}")
print()
