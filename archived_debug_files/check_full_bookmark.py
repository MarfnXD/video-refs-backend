"""Verificar bookmark completo"""
import os
from dotenv import load_dotenv
from supabase import create_client
import json

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bookmark antigo que funcionou (migrado anteriormente)
bookmark_id = 'd644e177-53c3-4c48-a79b-62cf7c03b89c'  # Do batch 3

result = supabase.table('bookmarks') \
    .select('*') \
    .eq('id', bookmark_id) \
    .execute()

if result.data:
    bm = result.data[0]

    print()
    print("=" * 80)
    print("BOOKMARK COMPLETO")
    print("=" * 80)
    print()
    print(f"ID: {bm['id']}")
    print(f"Status: {bm['processing_status']}")
    print(f"URL: {bm['url']}")
    print()
    print(f"Title: {bm.get('title')}")
    print(f"Platform: {bm.get('platform')}")
    print()
    print(f"Thumbnail (original): {bm.get('thumbnail', 'N/A')[:100] if bm.get('thumbnail') else 'N/A'}...")
    print(f"Cloud Thumbnail: {bm.get('cloud_thumbnail_url', 'N/A')[:100] if bm.get('cloud_thumbnail_url') else 'N/A'}...")
    print()

    if bm.get('metadata'):
        print("Metadata extraído:")
        metadata = bm['metadata']
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        print(f"  - Title: {metadata.get('title', 'N/A')}")
        print(f"  - Thumbnail URL: {metadata.get('thumbnail_url', 'N/A')[:100] if metadata.get('thumbnail_url') else 'N/A'}...")
        print()

    if bm.get('error_message'):
        print(f"Erro: {bm['error_message']}")
