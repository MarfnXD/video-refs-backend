"""
Busca bookmarks que contenham "FOOH" nos metadados
"""
from supabase import create_client
import os

SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

# Busca bookmarks com "FOOH" em qualquer campo
response = supabase.table("bookmarks").select("*").execute()
bookmarks = response.data

fooh_bookmarks = []

for b in bookmarks:
    fields_to_check = [
        ('title', b.get('title', '')),
        ('auto_description', b.get('auto_description', '')),
        ('user_context_raw', b.get('user_context_raw', '')),
        ('user_context_processed', b.get('user_context_processed', '')),
        ('tags', str(b.get('tags', []))),
        ('auto_tags', str(b.get('auto_tags', []))),
        ('categories', str(b.get('categories', []))),
        ('auto_categories', str(b.get('auto_categories', []))),
    ]

    # Check metadata
    metadata = b.get('metadata', {})
    if metadata:
        fields_to_check.append(('metadata.description', metadata.get('description', '')))
        fields_to_check.append(('metadata.hashtags', str(metadata.get('hashtags', []))))

    # Verifica se "FOOH" aparece em algum campo
    found_in = []
    for field_name, field_value in fields_to_check:
        if field_value and 'FOOH' in str(field_value).upper():
            found_in.append(field_name)

    if found_in:
        fooh_bookmarks.append({
            'id': b['id'],
            'title': b.get('title', 'N/A')[:60],
            'url': b.get('url', 'N/A')[:50],
            'found_in': found_in,
            'has_embedding': b.get('embedding') is not None
        })

print(f"\n📊 Total de bookmarks: {len(bookmarks)}")
print(f"🎯 Bookmarks com 'FOOH': {len(fooh_bookmarks)}\n")

if fooh_bookmarks:
    print("=" * 100)
    for i, b in enumerate(fooh_bookmarks, 1):
        print(f"\n{i}. {b['title']}")
        print(f"   URL: {b['url']}")
        print(f"   Encontrado em: {', '.join(b['found_in'])}")
        print(f"   Tem embedding: {'✅ SIM' if b['has_embedding'] else '❌ NÃO'}")
        print("-" * 100)
else:
    print("❌ Nenhum bookmark encontrado com 'FOOH'")
    print("\nSugestões:")
    print("1. Verifique se os bookmarks têm 'FOOH' em tags, categorias ou descrição")
    print("2. Verifique se o scraping extraiu os metadados corretamente")
