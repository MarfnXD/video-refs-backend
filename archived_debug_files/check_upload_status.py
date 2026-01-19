"""
Verificar status do upload dos 3 vídeos reprocessados
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BOOKMARK_IDS = [
    'c88c9c45-6fb4-49dd-b5df-374a9adfac3f',
    'c491cfd1-c1c5-410d-aeb3-6523c970d6e2',
    'd49a39ec-2fc1-4ef0-b8ed-0ce2b5d497e9',
]

print("="*80)
print("STATUS DO UPLOAD - 3 VÍDEOS REPROCESSADOS")
print("="*80)
print()

for idx, bookmark_id in enumerate(BOOKMARK_IDS, 1):
    result = supabase.table('bookmarks').select(
        'id, title, processing_status, cloud_video_url, thumbnail_url'
    ).eq('id', bookmark_id).execute()
    
    if not result.data:
        print(f"[{idx}] ❌ Bookmark não encontrado")
        continue
    
    bm = result.data[0]
    
    print(f"[{idx}] {bm['title'][:50]}...")
    print(f"    ID: {bm['id'][:8]}...")
    print(f"    Status: {bm['processing_status']}")
    print(f"    Cloud URL: {'✅ SIM' if bm.get('cloud_video_url') else '❌ NÃO'}")
    print(f"    Thumbnail: {'✅ SIM' if bm.get('thumbnail_url') else '❌ NÃO'}")
    print()

print("="*80)
