"""
Reprocessar os 15 vídeos que foram perdidos no crash de memória
IDs dos últimos 15 vídeos migrados (migrate_20_bookmark_ids.txt)
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

# Ler IDs dos bookmarks que foram perdidos
print("="*80)
print("REPROCESSAMENTO - 15 VÍDEOS PERDIDOS NO CRASH")
print("="*80)
print()

try:
    with open('migrate_20_bookmark_ids.txt', 'r') as f:
        bookmark_ids = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print("❌ Arquivo migrate_20_bookmark_ids.txt não encontrado")
    exit(1)

print(f"📋 Encontrados {len(bookmark_ids)} bookmarks para reprocessar")
print()

results = []

for idx, bookmark_id in enumerate(bookmark_ids, 1):
    # Buscar dados do bookmark
    bm_result = supabase.table('bookmarks').select('url, title, processing_status').eq('id', bookmark_id).execute()
    
    if not bm_result.data:
        print(f"[{idx}/{len(bookmark_ids)}] ❌ Bookmark não encontrado: {bookmark_id[:8]}")
        results.append({'bookmark_id': bookmark_id, 'success': False, 'error': 'Not found'})
        continue
    
    url = bm_result.data[0]['url']
    title = bm_result.data[0]['title'][:50]
    status = bm_result.data[0]['processing_status']
    
    print(f"[{idx}/{len(bookmark_ids)}] {title}...")
    print(f"  Status atual: {status}")
    
    # Se já completou, pular
    if status == 'completed':
        print(f"  ✅ Já processado")
        results.append({'bookmark_id': bookmark_id, 'success': True, 'skipped': True})
        print()
        continue
    
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
            job_id = job_data.get('job_id')
            estimated_time = job_data.get('estimated_time_seconds', 0)
            
            print(f"  ✅ Enfileirado: {job_id[:8] if job_id else 'N/A'}... ({estimated_time}s)")
            results.append({
                'bookmark_id': bookmark_id,
                'success': True,
                'job_id': job_id,
                'estimated_time': estimated_time
            })
        else:
            print(f"  ❌ Erro: HTTP {response.status_code}")
            results.append({'bookmark_id': bookmark_id, 'success': False, 'error': f'HTTP {response.status_code}'})
    
    except requests.exceptions.Timeout:
        print(f"  ⏱️  Timeout (backend processa mesmo assim)")
        results.append({'bookmark_id': bookmark_id, 'success': True, 'timeout': True})
    
    except Exception as e:
        print(f"  ❌ Erro: {str(e)[:60]}")
        results.append({'bookmark_id': bookmark_id, 'success': False, 'error': str(e)[:60]})
    
    print()

# Resumo
print("="*80)
print("📊 RESUMO")
print("="*80)
success_count = sum(1 for r in results if r['success'])
skipped_count = sum(1 for r in results if r.get('skipped'))
print(f"✅ Enfileirados: {success_count - skipped_count}/{len(bookmark_ids)}")
print(f"⏭️  Já processados: {skipped_count}")
print(f"❌ Falhas: {len(bookmark_ids) - success_count}")
print()

if success_count > skipped_count:
    total_time = sum(r.get('estimated_time', 0) for r in results if r['success'] and not r.get('skipped'))
    print(f"⏱️  Tempo total estimado: {total_time}s (~{total_time//60}min)")
    print()
    print("⚠️  ATENÇÃO: Agora com 1 worker (sequencial)")
    print("   Processamento será mais lento mas estável")
    print("   Evita crash por falta de memória")
