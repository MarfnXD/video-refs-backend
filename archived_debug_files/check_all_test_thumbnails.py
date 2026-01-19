"""
Verifica as thumbnails de todos os 5 bookmarks de teste
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

bookmark_ids = [
    '9d0a8bf8-3006-4c99-9b02-1b4b11cd1c5f',
    'eefc288c-655a-4abb-b1c7-ac79460d3cf6',
    '88788190-2bf6-474c-9391-60bc63c6c8ec',
    'f49ad048-d3b8-4669-b3f8-113c66a382f5',
    'a040b835-1d19-4d7f-ae17-0d52a024e7ce'
]

print("=" * 80)
print("🔍 VERIFICANDO THUMBNAILS DE TODOS OS BOOKMARKS DE TESTE")
print("=" * 80)
print()

broken = []
ok = []

for idx, bookmark_id in enumerate(bookmark_ids, 1):
    result = supabase.table('bookmarks').select('smart_title, cloud_thumbnail_url').eq('id', bookmark_id).single().execute()
    
    if not result.data:
        print(f"[{idx}/5] ❌ {bookmark_id} - Não encontrado")
        continue
    
    data = result.data
    title = data.get('smart_title', 'Sem título')[:40]
    cloud_thumb = data.get('cloud_thumbnail_url')
    
    print(f"[{idx}/5] {title}...")
    
    if not cloud_thumb:
        print(f"  ❌ NULL")
        broken.append(bookmark_id)
    else:
        # Verificar se a URL está completa (deve ter user_id/thumbnails/bookmark_id)
        expected_path = f"0ed9bb40-0041-4dca-9649-256cb418f403/thumbnails/{bookmark_id}"
        
        if expected_path in cloud_thumb:
            print(f"  ✅ OK: {cloud_thumb[:80]}...")
            ok.append(bookmark_id)
        else:
            print(f"  ❌ TRUNCADA/CORROMPIDA:")
            print(f"     {cloud_thumb}")
            broken.append(bookmark_id)
    
    print()

print("=" * 80)
print(f"✅ Thumbnails OK: {len(ok)}/5")
print(f"❌ Thumbnails com problema: {len(broken)}/5")

if broken:
    print()
    print("⚠️  Precisa reprocessar as thumbnails!")
    print("   Rode: python fix_missing_thumbnails.py")
