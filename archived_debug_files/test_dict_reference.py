"""
Testa se metadata dict está sendo modificado por referência
"""

# Simular o que acontece no background_processor
metadata = {
    'thumbnail_url': 'https://cdninstagram.com/original.jpg',
    'title': 'Test'
}

print("=" * 80)
print("🧪 TESTE DE REFERÊNCIA DE DICIONÁRIO")
print("=" * 80)
print()

print("1. metadata original:")
print(f"   thumbnail_url: {metadata['thumbnail_url']}")
print()

# Simular linha 235
update_data = {}
update_data['thumbnail'] = metadata.get('thumbnail_url')
print("2. Após update_data['thumbnail'] = metadata.get('thumbnail_url'):")
print(f"   update_data['thumbnail']: {update_data['thumbnail']}")
print(f"   metadata['thumbnail_url']: {metadata['thumbnail_url']}")
print()

# Simular linha 248
instagram_thumbnail_url = metadata.get('thumbnail_url')
print("3. instagram_thumbnail_url = metadata.get('thumbnail_url'):")
print(f"   instagram_thumbnail_url: {instagram_thumbnail_url}")
print()

# Simular upload que retorna URL do Supabase
cloud_thumbnail_url = "https://supabase.co/storage/v1/object/public/thumbnails/abc123.jpg"
update_data['cloud_thumbnail_url'] = cloud_thumbnail_url
print("4. cloud_thumbnail_url = '...(Supabase)':")
print(f"   cloud_thumbnail_url: {cloud_thumbnail_url}")
print(f"   metadata['thumbnail_url']: {metadata['thumbnail_url']}")
print()

# Simular linha 279
update_data['metadata'] = metadata
print("5. update_data['metadata'] = metadata:")
print(f"   update_data['metadata']['thumbnail_url']: {update_data['metadata']['thumbnail_url']}")
print()

# Verificar se são o mesmo objeto
print("6. Verificação:")
print(f"   metadata is update_data['metadata']: {metadata is update_data['metadata']}")
print(f"   Se True, significa que qualquer modificação em metadata afeta update_data!")
print()

print("=" * 80)
