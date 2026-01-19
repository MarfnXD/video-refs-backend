import os
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Buscar os 5 primeiros bookmarks para ver estrutura
result = supabase.table('bookmarks').select('id, title, smart_title, thumbnail_url, cloud_thumbnail_url').limit(10).execute()

print("=" * 80)
print("ANÁLISE DAS THUMBNAILS NO BANCO")
print("=" * 80)
print()

for item in result.data:
    print(f"ID: {item['id'][:8]}...")
    print(f"Título: {item.get('smart_title') or item.get('title', 'N/A')[:60]}")
    print(f"thumbnail_url: {item.get('thumbnail_url', 'NULL')[:80] if item.get('thumbnail_url') else 'NULL'}")
    print(f"cloud_thumbnail_url: {item.get('cloud_thumbnail_url', 'NULL')[:80] if item.get('cloud_thumbnail_url') else 'NULL'}")
    print("-" * 80)
    print()

# Estatísticas
total = len(result.data)
with_cloud = sum(1 for x in result.data if x.get('cloud_thumbnail_url'))
with_original = sum(1 for x in result.data if x.get('thumbnail_url'))

print("\nESTATÍSTICAS:")
print(f"Total de bookmarks analisados: {total}")
print(f"Com cloud_thumbnail_url: {with_cloud} ({with_cloud/total*100:.0f}%)")
print(f"Com thumbnail_url original: {with_original} ({with_original/total*100:.0f}%)")
