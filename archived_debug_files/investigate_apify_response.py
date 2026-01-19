"""
Investiga: o Apify realmente retornou URL do Supabase?
Ou isso foi salvo depois de algum processamento?
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🔍 INVESTIGANDO TODOS OS BOOKMARKS COM metadata.thumbnail_url CORROMPIDA")
print("=" * 80)
print()

# Buscar todos os bookmarks
result = supabase.table('bookmarks')\
    .select('id, smart_title, url, metadata, cloud_thumbnail_url, created_at')\
    .eq('user_id', USER_ID)\
    .execute()

bookmarks = result.data or []

# Filtrar os que têm thumbnail_url no metadata apontando para Supabase
corrupted = []
valid = []

for bm in bookmarks:
    metadata = bm.get('metadata') or {}
    thumb_url = metadata.get('thumbnail_url')
    
    if thumb_url:
        if 'supabase' in thumb_url.lower():
            corrupted.append(bm)
        else:
            valid.append(bm)

print(f"Total de bookmarks: {len(bookmarks)}")
print(f"Com thumbnail_url válida (Instagram): {len(valid)}")
print(f"Com thumbnail_url CORROMPIDA (Supabase): {len(corrupted)}")
print()

if corrupted:
    print("=" * 80)
    print("❌ BOOKMARKS COM metadata.thumbnail_url CORROMPIDA:")
    print("=" * 80)
    print()
    
    for bm in corrupted:
        print(f"ID: {bm['id']}")
        print(f"Título: {bm.get('smart_title', 'Sem título')[:60]}...")
        print(f"Instagram URL: {bm['url']}")
        print(f"Criado em: {bm['created_at'][:19]}")
        
        metadata = bm.get('metadata') or {}
        thumb_meta = metadata.get('thumbnail_url')
        cloud_thumb = bm.get('cloud_thumbnail_url')
        
        print(f"metadata.thumbnail_url: {thumb_meta[:80] if thumb_meta else 'NULL'}...")
        print(f"cloud_thumbnail_url:    {cloud_thumb[:80] if cloud_thumb else 'NULL'}...")
        
        # Verificar se são iguais (isso indicaria que apenas copiou)
        if thumb_meta == cloud_thumb:
            print(f"⚠️  MESMA URL → backend copiou metadata.thumbnail_url para cloud_thumbnail_url")
        
        print()

    print("=" * 80)
    print("🔬 ANÁLISE")
    print("=" * 80)
    print()
    
    # Verificar datas
    dates = [bm['created_at'][:10] for bm in corrupted]
    unique_dates = list(set(dates))
    
    print(f"Datas de criação dos corrompidos:")
    for date in sorted(unique_dates):
        count = dates.count(date)
        print(f"  {date}: {count} bookmarks")
    
    print()
    print("💡 POSSÍVEIS CAUSAS:")
    print()
    print("1. Bug no Apify (improvável - nunca vi Apify retornar URL do cliente)")
    print("2. Bug no nosso código que sobrescreveu metadata depois")
    print("3. Migração anterior que tinha lógica diferente")
    print("4. Teste manual que inseriu dados incorretos")
    print()
    
    # Verificar padrões nas URLs do Instagram
    print("Padrões das URLs do Instagram:")
    instagram_urls = [bm['url'] for bm in corrupted]
    
    share_reel = sum(1 for url in instagram_urls if '/share/reel/' in url)
    normal_reel = sum(1 for url in instagram_urls if '/reel/' in url and '/share/' not in url)
    
    print(f"  /share/reel/: {share_reel}")
    print(f"  /reel/ (normal): {normal_reel}")
    print()
    
else:
    print("✅ Nenhum bookmark com metadata.thumbnail_url corrompida!")
    print("   Todos têm URLs válidas do Instagram CDN.")

print("=" * 80)
