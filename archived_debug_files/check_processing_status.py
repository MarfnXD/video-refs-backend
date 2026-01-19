"""
Verificar status de todos os vídeos em processamento
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Buscar todos os bookmarks do usuário ordenados por data (mais recentes primeiro)
result = supabase.table('bookmarks').select(
    'id, title, processing_status, cloud_video_url, created_at'
).eq('user_id', USER_ID).order('created_at', desc=True).limit(20).execute()

print("="*80)
print("STATUS DOS ÚLTIMOS 20 VÍDEOS")
print("="*80)
print()

status_counts = {
    'completed': 0,
    'processing': 0,
    'queued': 0,
    'failed': 0
}

completed_with_cloud = 0
completed_without_cloud = 0

for idx, bm in enumerate(result.data, 1):
    status = bm['processing_status']
    has_cloud = bool(bm.get('cloud_video_url'))
    
    status_counts[status] = status_counts.get(status, 0) + 1
    
    if status == 'completed':
        if has_cloud:
            completed_with_cloud += 1
        else:
            completed_without_cloud += 1
    
    # Emoji por status
    if status == 'completed':
        emoji = '✅' if has_cloud else '⚠️'
    elif status == 'processing':
        emoji = '⏳'
    elif status == 'queued':
        emoji = '📋'
    else:
        emoji = '❌'
    
    cloud_status = '☁️' if has_cloud else '🚫'
    
    print(f"[{idx:2d}] {emoji} {status:12s} {cloud_status} {bm['title'][:50]}")

print()
print("="*80)
print("📊 RESUMO")
print("="*80)
print(f"✅ Completed: {status_counts['completed']} (com cloud: {completed_with_cloud}, sem cloud: {completed_without_cloud})")
print(f"⏳ Processing: {status_counts['processing']}")
print(f"📋 Queued: {status_counts['queued']}")
print(f"❌ Failed: {status_counts['failed']}")
print()

if status_counts['processing'] > 0 or status_counts['queued'] > 0:
    print("⏰ Ainda há vídeos sendo processados...")
else:
    print("✅ Todos os vídeos foram processados!")
