"""Verificar status das thumbnails no banco"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Buscar bookmarks completed com cloud_thumbnail_url
response = supabase.table('bookmarks') \
    .select('id, cloud_thumbnail_url') \
    .eq('processing_status', 'completed') \
    .not_.is_('cloud_thumbnail_url', 'null') \
    .execute()

total = len(response.data)
supabase_storage = 0
instagram_cdn = 0

for bm in response.data:
    url = bm['cloud_thumbnail_url']
    if 'supabase.co' in url:
        supabase_storage += 1
    elif 'instagram.com' in url or 'cdninstagram.com' in url:
        instagram_cdn += 1

print("=" * 60)
print("📊 STATUS FINAL DAS THUMBNAILS")
print("=" * 60)
print(f"Total de bookmarks completed: {total}")
print()
print(f"✅ Supabase Storage: {supabase_storage} ({supabase_storage*100//total}%)")
print(f"❌ Instagram CDN:     {instagram_cdn} ({instagram_cdn*100//total if total > 0 else 0}%)")
print()
print("✅ MIGRAÇÃO 100% COMPLETA!" if instagram_cdn == 0 else "⚠️  Ainda há thumbnails do Instagram")
