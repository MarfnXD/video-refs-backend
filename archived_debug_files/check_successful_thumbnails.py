"""Verificar bookmarks com thumbnail no Supabase Storage"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Buscar alguns bookmarks que têm cloud_thumbnail_url do Supabase
response = supabase.table('bookmarks') \
    .select('id, url, thumbnail, cloud_thumbnail_url, processing_status') \
    .eq('processing_status', 'completed') \
    .like('cloud_thumbnail_url', '%supabase%') \
    .limit(5) \
    .execute()

print("=" * 80)
print("BOOKMARKS COM THUMBNAIL NO SUPABASE STORAGE (FUNCIONANDO)")
print("=" * 80)
print()

for idx, bm in enumerate(response.data, 1):
    print(f"[{idx}] {bm['id'][:8]}...")
    print(f"    URL: {bm['url']}")
    print(f"    Thumbnail original: {bm.get('thumbnail', 'N/A')[:80] if bm.get('thumbnail') else 'N/A'}...")
    print(f"    Cloud Thumbnail: {bm.get('cloud_thumbnail_url', 'N/A')[:80] if bm.get('cloud_thumbnail_url') else 'N/A'}...")
    print()
