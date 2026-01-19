"""
Script para REPROCESSAR 3 vídeos que falharam no upload
- Usa endpoint /api/process-bookmark-complete com force_reprocess
- Testa fix de retry automático para downloads grandes
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# IDs dos bookmarks que falharam no upload
BOOKMARK_IDS = [
    'c88c9c45-6fb4-49dd-b5df-374a9adfac3f',  # Preguiça não é descanso
    'c491cfd1-c1c5-410d-aeb3-6523c970d6e2',  # Runway Vdo-to-Vdo
    'd49a39ec-2fc1-4ef0-b8ed-0ce2b5d497e9',  # Live the Legend
]

print("="*80)
print("REPROCESSAMENTO - 3 VÍDEOS QUE FALHARAM NO UPLOAD")
print("="*80)
print()
print("🔥 Testando fix de retry automático para downloads grandes")
print(f"   - Retry: 3 tentativas")
print(f"   - Backoff exponencial: 2s, 4s, 8s")
print(f"   - Chunks maiores: 64KB")
print(f"   - Timeouts otimizados")
print()

results = []

for idx, bookmark_id in enumerate(BOOKMARK_IDS, 1):
    # Buscar URL do bookmark
    bm_result = supabase.table('bookmarks').select('url, title').eq('id', bookmark_id).execute()
    
    if not bm_result.data:
        print(f"[{idx}/{len(BOOKMARK_IDS)}] ❌ Bookmark não encontrado: {bookmark_id[:8]}")
        results.append({
            'bookmark_id': bookmark_id,
            'success': False,
            'error': 'Bookmark não encontrado'
        })
        print()
        continue
    
    url = bm_result.data[0]['url']
    title = bm_result.data[0]['title']
    
    print(f"[{idx}/{len(BOOKMARK_IDS)}] Reprocessando: {title[:40]}...")
    print(f"  URL: {url[:60]}...")
    
    try:
        # Chamar endpoint padrão com upload_to_cloud=True
        response = requests.post(
            f'{BACKEND_URL}/api/process-bookmark-complete',
            json={
                'bookmark_id': bookmark_id,
                'user_id': USER_ID,
                'url': url,
                'upload_to_cloud': True,  # Forçar upload
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
            
            print(f"  ✅ Enfileirado: job_id={job_id}")
            print(f"  ⏱️  Tempo estimado: {estimated_time}s")
            
            results.append({
                'bookmark_id': bookmark_id,
                'success': True,
                'job_id': job_id,
                'estimated_time': estimated_time
            })
        else:
            print(f"  ❌ Erro: HTTP {response.status_code}")
            print(f"  {response.text[:100]}")
            
            results.append({
                'bookmark_id': bookmark_id,
                'success': False,
                'error': f"HTTP {response.status_code}"
            })
    
    except Exception as e:
        print(f"  ❌ Erro: {str(e)[:100]}")
        
        results.append({
            'bookmark_id': bookmark_id,
            'success': False,
            'error': str(e)[:100]
        })
    
    print()

# Resumo
print("="*80)
print("📊 RESUMO")
print("="*80)
print()

success_count = sum(1 for r in results if r['success'])
print(f"✅ Enfileirados: {success_count}/{len(BOOKMARK_IDS)}")
print(f"❌ Falhas: {len(BOOKMARK_IDS) - success_count}")
print()

if success_count > 0:
    total_time = sum(r.get('estimated_time', 0) for r in results if r['success'])
    print(f"⏱️  Tempo total estimado: {total_time}s (~{total_time//60}min)")
    print()
    print("⏰ Processamento em andamento no servidor Render...")
    print("   Acompanhe via Supabase dashboard")
    print()
    print("🔍 Para verificar se upload funcionou:")
    print("   - Checar se cloud_video_url está preenchido")
    print("   - Verificar thumbnails nos cards do app")

# Salvar log
log_file = f'reprocess_3_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
with open(log_file, 'w') as f:
    f.write(f"REPROCESSAMENTO - {datetime.now()}\n")
    f.write("="*80 + "\n\n")
    f.write(f"Total: {len(BOOKMARK_IDS)}\n")
    f.write(f"Sucesso: {success_count}\n")
    f.write(f"Falhas: {len(BOOKMARK_IDS) - success_count}\n\n")
    
    for r in results:
        bm_id = r['bookmark_id'][:8]
        if r['success']:
            f.write(f"✅ {bm_id}: job_id={r['job_id']}\n")
        else:
            f.write(f"❌ {bm_id}: {r['error']}\n")

print(f"📄 Log salvo: {log_file}")
print()
