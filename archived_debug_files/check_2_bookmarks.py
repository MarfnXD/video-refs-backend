"""
Verifica se os 2 bookmarks foram processados corretamente
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

bookmark_ids = [
    '9cb53251-5769-4c4f-8bd9-d7d212ff4f29',
    '1776b584-4bd7-4d7a-9d67-d45841910831'
]

print("=" * 80)
print("🔍 VERIFICANDO BOOKMARKS")
print("=" * 80)
print()

for bookmark_id in bookmark_ids:
    short_id = bookmark_id[:8]
    result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()
    bookmark = result.data
    
    print(f"📋 Bookmark {short_id}:")
    print(f"   Status: {bookmark['processing_status']}")
    print(f"   Platform: {bookmark.get('platform', 'N/A')}")
    print()
    
    # Verificar campos críticos
    metadata = bookmark.get('metadata') or {}
    cloud_thumb = bookmark.get('cloud_thumbnail_url')
    thumb_meta = metadata.get('thumbnail_url')
    
    print(f"   cloud_thumbnail_url: {cloud_thumb[:80] if cloud_thumb else 'NULL'}...")
    print(f"   metadata.thumbnail_url: {thumb_meta[:80] if thumb_meta else 'NULL'}...")
    print()
    
    # Validar
    has_issues = False
    
    if not cloud_thumb or 'supabase' not in cloud_thumb.lower():
        has_issues = True
        print(f"   ❌ cloud_thumbnail_url incorreta")
    
    if not thumb_meta:
        has_issues = True
        print(f"   ❌ metadata.thumbnail_url NULL")
    elif 'supabase' in thumb_meta.lower():
        has_issues = True
        print(f"   ❌ metadata.thumbnail_url CORROMPIDA (Supabase)")
    elif 'instagram' not in thumb_meta and 'cdninstagram' not in thumb_meta:
        has_issues = True
        print(f"   ❌ metadata.thumbnail_url não é Instagram CDN")
    
    if not has_issues:
        print(f"   ✅ TUDO CERTO!")
    
    print()
    print("=" * 80)
    print()
