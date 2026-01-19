"""
Debug completo do bookmark 1776b584 que falhou
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

bookmark_id = '1776b584-4bd7-4d7a-9d67-d45841910831'

result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()
bookmark = result.data

print("=" * 80)
print(f"🔍 DEBUG COMPLETO - Bookmark {bookmark_id[:8]}")
print("=" * 80)
print()

print(f"URL: {bookmark['url']}")
print(f"Platform: {bookmark.get('platform')}")
print(f"Status: {bookmark['processing_status']}")
print()

metadata = bookmark.get('metadata') or {}

print("🔍 METAD ATA COMPLETA:")
print(f"   thumbnail_url: {metadata.get('thumbnail_url')}")
print()

print("🔍 CAMPOS DA TABELA:")
print(f"   cloud_thumbnail_url: {bookmark.get('cloud_thumbnail_url')}")
print(f"   thumbnail: {bookmark.get('thumbnail')}")
print()

print("🎯 ANÁLISE:")
print()

# Verificar se thumbnail_url do metadata é Supabase
if metadata.get('thumbnail_url') and 'supabase' in metadata['thumbnail_url'].lower():
    print("❌ metadata.thumbnail_url está CORROMPIDO (contém supabase)")
    print()
    print("Valor corrompido:")
    print(f"   {metadata['thumbnail_url']}")
    print()
    
    # Verificar se é a mesma URL do cloud_thumbnail_url
    if metadata['thumbnail_url'] == bookmark.get('cloud_thumbnail_url'):
        print("🔍 metadata.thumbnail_url === cloud_thumbnail_url")
        print("   Isso significa que cloud_thumbnail_url foi copiado para metadata!")
    elif '/object/public/thumbnails/' in metadata['thumbnail_url']:
        print("🔍 metadata.thumbnail_url contém '/object/public/thumbnails/'")
        print("   Isso é path do StorageService antigo (deprecated)!")
        print("   Path correto deveria ser: /{user_id}/thumbnails/{bookmark_id}.jpg")
    
print()
print("=" * 80)
