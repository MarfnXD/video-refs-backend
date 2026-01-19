"""Verificar detalhes dos vídeos de teste"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# IDs dos 3 vídeos de teste
test_ids = [
    'e7c02fc7-ee39-42cd-9652-f0d67e6f9d5c',
    'f457a515-8c79-4b37-ad46-69378b70fad1',
    '3865279a-22ef-427c-bbc7-2d0d7cd7eaaa'
]

print("=" * 80)
print("DETALHES DOS VÍDEOS DE TESTE")
print("=" * 80)
print()

for idx, bookmark_id in enumerate(test_ids, 1):
    result = supabase.table('bookmarks') \
        .select('id, processing_status, error_message, url, cloud_thumbnail_url, thumbnail') \
        .eq('id', bookmark_id) \
        .execute()

    if result.data:
        bm = result.data[0]
        print(f"[{idx}/3] {bookmark_id[:8]}...")
        print(f"        Status: {bm['processing_status']}")
        print(f"        URL: {bm['url']}")

        if bm.get('thumbnail'):
            print(f"        Thumbnail: {bm['thumbnail'][:70]}...")
        else:
            print(f"        Thumbnail: N/A")

        if bm.get('cloud_thumbnail_url'):
            is_supabase = 'supabase.co' in bm['cloud_thumbnail_url']
            is_instagram = 'instagram.com' in bm['cloud_thumbnail_url'] or 'cdninstagram.com' in bm['cloud_thumbnail_url']

            print(f"        Cloud Thumb: {bm['cloud_thumbnail_url'][:70]}...")

            if is_supabase:
                print(f"        ✅ CORRETO - Supabase Storage")
            elif is_instagram:
                print(f"        ❌ ERRO - Instagram CDN")
            else:
                print(f"        ⚠️  OUTRO DOMÍNIO")
        else:
            print(f"        Cloud Thumb: N/A")

        if bm.get('error_message'):
            print(f"        Erro: {bm['error_message'][:200]}")
        print()
