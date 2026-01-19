"""
Teste final: 2 bookmarks após force redeploy
"""
import os
import csv
import time
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'
CSV_FILE = 'instagram_urls_migrated_20251226_214730.csv'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🧪 TESTE FINAL - 2 Bookmarks (Validar Correção Pós-Redeploy)")
print("=" * 80)
print()

# Pegar 2 URLs não migradas
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    nao_migradas = [row for row in reader if row['migrado'] == 'NÃO']

urls_teste = nao_migradas[:2]

print(f"URLs selecionadas:")
for row in urls_teste:
    print(f"  ID {row['ID']}: {row['URL'][:60]}...")
print()

bookmarks_criados = []

for row in urls_teste:
    url = row['URL']
    csv_id = row['ID']

    # Verificar se já existe
    existing = supabase.table('bookmarks').select('id').eq('url', url).eq('user_id', USER_ID).execute()
    if existing.data:
        supabase.table('bookmarks').delete().eq('id', existing.data[0]['id']).execute()

    # Criar
    result = supabase.table('bookmarks').insert({
        'user_id': USER_ID,
        'url': url,
        'processing_status': 'pending'
    }).execute()

    bookmark_id = result.data[0]['id']

    # Enfileirar
    response = requests.post(
        'https://video-refs-backend.onrender.com/api/process-bookmark-complete',
        json={
            'bookmark_id': bookmark_id,
            'url': url,
            'user_id': USER_ID,
            'upload_to_cloud': True,
            'analyze_video': False
        }
    )

    if response.status_code == 200:
        bookmarks_criados.append({
            'csv_id': csv_id,
            'bookmark_id': bookmark_id,
            'url': url
        })
        print(f"[{csv_id}] ✅ Criado e enfileirado: {bookmark_id[:8]}...")
    else:
        print(f"[{csv_id}] ❌ Erro: {response.status_code}")

print()
print(f"⏳ Aguardando processamento (max 2 min)...")
print()

max_wait = 120
start_time = time.time()

while (time.time() - start_time) < max_wait:
    completed = 0
    failed = 0

    for bm in bookmarks_criados:
        result = supabase.table('bookmarks').select('processing_status').eq('id', bm['bookmark_id']).single().execute()
        status = result.data['processing_status']
        if status == 'completed':
            completed += 1
        elif status == 'failed':
            failed += 1

    elapsed = int(time.time() - start_time)
    print(f"   [{elapsed}s] Completed: {completed}/{len(bookmarks_criados)} | Failed: {failed}", end='\r')

    if completed + failed == len(bookmarks_criados):
        print()
        print()
        break

    time.sleep(3)

print("=" * 80)
print("🔍 VALIDAÇÃO DETALHADA")
print("=" * 80)
print()

ok_count = 0
fail_count = 0

for bm in bookmarks_criados:
    result = supabase.table('bookmarks').select('*').eq('id', bm['bookmark_id']).single().execute()
    bookmark = result.data

    print(f"[CSV ID {bm['csv_id']}] {bm['url'][:50]}...")
    print(f"  Bookmark: {bm['bookmark_id'][:8]}...")
    print(f"  Status: {bookmark['processing_status']}")
    print(f"  Smart Title: {bookmark.get('smart_title', 'NULL')[:60]}...")
    print()

    if bookmark['processing_status'] == 'completed':
        metadata = bookmark.get('metadata') or {}
        cloud_thumb = bookmark.get('cloud_thumbnail_url')
        thumb_meta = metadata.get('thumbnail_url')

        print(f"  1️⃣ cloud_thumbnail_url:")
        if cloud_thumb and 'supabase' in cloud_thumb.lower():
            print(f"     ✅ {cloud_thumb[:70]}...")
        else:
            print(f"     ❌ {cloud_thumb or 'NULL'}")

        print()
        print(f"  2️⃣ metadata.thumbnail_url:")
        if thumb_meta:
            if 'instagram' in thumb_meta or 'cdninstagram' in thumb_meta:
                print(f"     ✅ {thumb_meta[:70]}...")
                print(f"     🎉 Instagram CDN preservada!")
                ok_count += 1
            elif 'supabase' in thumb_meta.lower():
                print(f"     ❌ {thumb_meta[:70]}...")
                print(f"     ❌ CORROMPIDA com URL do Supabase!")
                fail_count += 1
            else:
                print(f"     ⚠️  {thumb_meta[:70]}...")
                fail_count += 1
        else:
            print(f"     ❌ NULL")
            fail_count += 1
    else:
        print(f"  ❌ Falhou: {bookmark.get('error_message', 'N/A')}")
        fail_count += 1

    print()

print("=" * 80)
print("📊 RESULTADO FINAL")
print("=" * 80)
print()

if ok_count == len(bookmarks_criados):
    print(f"✅✅✅ TESTE 100% APROVADO! ✅✅✅")
    print()
    print(f"   {ok_count}/{len(bookmarks_criados)} bookmarks com campos corretos")
    print(f"   - cloud_thumbnail_url → Supabase Storage")
    print(f"   - metadata.thumbnail_url → Instagram CDN original")
    print()
    print(f"🎉 Correção do bug VALIDADA!")
    print(f"🚀 Pode prosseguir com migração completa!")
elif ok_count > 0:
    print(f"⚠️  TESTE PARCIAL: {ok_count}/{len(bookmarks_criados)} OK")
    print(f"   Ainda há {fail_count} bookmark(s) com problema")
else:
    print(f"❌ TESTE FALHOU: 0/{len(bookmarks_criados)} OK")
    print(f"   Bug ainda não foi corrigido")

print()
print("=" * 80)
