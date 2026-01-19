"""
Analisa diferenças entre thumbnails que funcionaram vs quebradas
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

bookmark_ids = {
    '9d0a8bf8-3006-4c99-9b02-1b4b11cd1c5f': 'QUEBRADA (Instagram CDN)',
    'eefc288c-655a-4abb-b1c7-ac79460d3cf6': 'QUEBRADA (Supabase truncado)',
    '88788190-2bf6-474c-9391-60bc63c6c8ec': 'OK',
    'f49ad048-d3b8-4669-b3f8-113c66a382f5': 'QUEBRADA (Supabase truncado)',
    'a040b835-1d19-4d7f-ae17-0d52a024e7ce': 'OK'
}

print("=" * 80)
print("🔍 ANALISANDO DIFERENÇAS ENTRE THUMBNAILS OK vs QUEBRADAS")
print("=" * 80)
print()

for bookmark_id, status in bookmark_ids.items():
    result = supabase.table('bookmarks').select('url, metadata, cloud_thumbnail_url').eq('id', bookmark_id).single().execute()
    
    if not result.data:
        continue
        
    data = result.data
    metadata = data.get('metadata') or {}
    instagram_url = data.get('url')
    cloud_thumb = data.get('cloud_thumbnail_url')
    original_thumb = metadata.get('thumbnail_url')
    
    print(f"[{status}]")
    print(f"  Instagram URL: {instagram_url}")
    print(f"  Thumbnail original: {original_thumb[:80] if original_thumb else 'NULL'}...")
    print(f"  cloud_thumbnail_url: {cloud_thumb[:80] if cloud_thumb else 'NULL'}...")
    print()

print("=" * 80)
print("💡 ANÁLISE")
print("=" * 80)
print()
print("Hipóteses:")
print("1. URLs do tipo /share/reel/ podem ter metadados diferentes")
print("2. Algumas thumbnails do Instagram retornam 403")
print("3. Processamento assíncrono pode ter race conditions")
print()
