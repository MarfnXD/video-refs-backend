"""
Verificar status real dos 15 vídeos
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ler IDs
with open('migrate_20_bookmark_ids.txt', 'r') as f:
    bookmark_ids = [line.strip() for line in f if line.strip()]

print("="*80)
print("STATUS REAL DOS 15 VÍDEOS")
print("="*80)
print()

status_counts = {'completed': 0, 'processing': 0, 'queued': 0, 'failed': 0}
with_cloud = 0
without_cloud = 0

for idx, bookmark_id in enumerate(bookmark_ids, 1):
    result = supabase.table('bookmarks').select(
        'title, processing_status, cloud_video_url'
    ).eq('id', bookmark_id).execute()
    
    if not result.data:
        continue
    
    bm = result.data[0]
    status = bm['processing_status']
    has_cloud = bool(bm.get('cloud_video_url'))
    
    status_counts[status] = status_counts.get(status, 0) + 1
    
    if status == 'completed':
        if has_cloud:
            with_cloud += 1
            emoji = '✅'
        else:
            without_cloud += 1
            emoji = '⚠️'
    elif status == 'processing':
        emoji = '⏳'
    elif status == 'queued':
        emoji = '📋'
    else:
        emoji = '❌'
    
    cloud_status = '☁️' if has_cloud else '🚫'
    
    print(f"[{idx:2d}] {emoji} {status:12s} {cloud_status} {bm['title'][:40]}")

print()
print("="*80)
print("📊 RESUMO")
print("="*80)
print(f"✅ Completed: {status_counts['completed']} (com cloud: {with_cloud}, sem cloud: {without_cloud})")
print(f"⏳ Processing: {status_counts['processing']}")
print(f"📋 Queued: {status_counts['queued']}")
print(f"❌ Failed: {status_counts.get('failed', 0)}")
print()

if status_counts['processing'] > 0 or status_counts['queued'] > 0:
    print("⏰ Ainda há vídeos sendo processados...")
else:
    print("✅ Todos finalizados!")
