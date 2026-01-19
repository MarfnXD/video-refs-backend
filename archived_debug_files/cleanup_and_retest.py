"""
Limpa bookmarks de teste anteriores e processa novamente + 5 novos
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
print("🗑️  PASSO 1: DELETANDO BOOKMARKS DE TESTES ANTERIORES")
print("=" * 80)
print()

# IDs dos bookmarks dos testes anteriores (os que já foram migrados no CSV)
# IDs 6, 7, 9, 10, 11, 76, 77 do CSV
test_csv_ids = ['6', '7', '9', '10', '11', '76', '77']

# Buscar URLs desses IDs no CSV
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    test_urls = [row['URL'] for row in reader if row['ID'] in test_csv_ids]

print(f"Deletando bookmarks de {len(test_urls)} URLs de teste...")
print()

deleted_count = 0
for url in test_urls:
    result = supabase.table('bookmarks').select('id, smart_title').eq('url', url).eq('user_id', USER_ID).execute()

    if result.data:
        for bm in result.data:
            print(f"  Deletando: {bm['id'][:8]}... - {bm.get('smart_title', 'N/A')[:40]}...")
            supabase.table('bookmarks').delete().eq('id', bm['id']).execute()
            deleted_count += 1

print()
print(f"✅ {deleted_count} bookmarks deletados")
print()

print("=" * 80)
print("📝 PASSO 2: RESETANDO CSV")
print("=" * 80)
print()

# Resetar os IDs do CSV para NÃO
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for row in rows:
    if row['ID'] in test_csv_ids:
        row['migrado'] = 'NÃO'
        row['data_migracao'] = ''

with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ {len(test_csv_ids)} URLs resetadas para NÃO no CSV")
print()

print("=" * 80)
print("🧪 PASSO 3: PROCESSANDO 12 BOOKMARKS (7 anteriores + 5 novos)")
print("=" * 80)
print()

# Pegar 12 URLs não migradas do CSV (isso vai incluir as 7 que acabamos de resetar + 5 novas)
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    nao_migradas = [row for row in reader if row['migrado'] == 'NÃO']

urls_teste = nao_migradas[:12]

print(f"URLs selecionadas:")
for row in urls_teste:
    print(f"  ID {row['ID']}: {row['URL'][:60]}...")
print()

bookmarks_criados = []

for row in urls_teste:
    url = row['URL']
    csv_id = row['ID']

    print(f"[{csv_id}] Criando: {url[:50]}...")

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
        print(f"  ✅ Enfileirado: {bookmark_id[:8]}...")
    else:
        print(f"  ❌ Erro: {response.status_code}")

    print()

print("=" * 80)
print(f"⏳ AGUARDANDO PROCESSAMENTO (max 4 minutos para 12 bookmarks)")
print("=" * 80)
print()

max_wait = 240
start_time = time.time()

while (time.time() - start_time) < max_wait:
    pending = 0
    processing = 0
    completed = 0
    failed = 0

    for bm in bookmarks_criados:
        result = supabase.table('bookmarks').select('processing_status').eq('id', bm['bookmark_id']).single().execute()
        status = result.data['processing_status']

        if status == 'pending':
            pending += 1
        elif status == 'processing':
            processing += 1
        elif status == 'completed':
            completed += 1
        elif status == 'failed':
            failed += 1

    elapsed = int(time.time() - start_time)
    print(f"   [{elapsed}s] Pending: {pending} | Processing: {processing} | Completed: {completed} | Failed: {failed}", end='\r')

    if completed + failed == len(bookmarks_criados):
        print()
        print()
        print(f"✅ Todos processados!")
        break

    time.sleep(3)

print()
print("=" * 80)
print("🔍 VALIDAÇÃO DOS RESULTADOS")
print("=" * 80)
print()

ok_count = 0
fail_count = 0
issues = []

for bm in bookmarks_criados:
    result = supabase.table('bookmarks').select('*').eq('id', bm['bookmark_id']).single().execute()
    bookmark = result.data

    csv_id = bm['csv_id']
    status = bookmark['processing_status']

    if status == 'completed':
        metadata = bookmark.get('metadata') or {}
        cloud_thumb = bookmark.get('cloud_thumbnail_url')
        thumb_meta = metadata.get('thumbnail_url')

        # Validar
        has_issues = False

        if not cloud_thumb or 'supabase' not in cloud_thumb.lower():
            has_issues = True
            issues.append(f"CSV ID {csv_id}: cloud_thumbnail_url incorreta")

        if not thumb_meta:
            has_issues = True
            issues.append(f"CSV ID {csv_id}: metadata.thumbnail_url NULL")
        elif 'supabase' in thumb_meta.lower():
            has_issues = True
            issues.append(f"CSV ID {csv_id}: metadata.thumbnail_url CORROMPIDA (Supabase)")
        elif 'instagram' not in thumb_meta and 'cdninstagram' not in thumb_meta:
            has_issues = True
            issues.append(f"CSV ID {csv_id}: metadata.thumbnail_url não é Instagram CDN")

        if has_issues:
            fail_count += 1
            print(f"❌ [CSV ID {csv_id}] {bm['url'][:40]}...")
        else:
            ok_count += 1
            print(f"✅ [CSV ID {csv_id}] {bm['url'][:40]}...")
    else:
        fail_count += 1
        issues.append(f"CSV ID {csv_id}: Processamento falhou - {bookmark.get('error_message', 'N/A')}")
        print(f"❌ [CSV ID {csv_id}] FALHOU - {bookmark.get('error_message', 'N/A')[:30]}...")

print()
print("=" * 80)
print("📊 RESULTADO FINAL")
print("=" * 80)
print()

if ok_count == len(bookmarks_criados):
    print(f"✅✅✅ TESTE 100% APROVADO! ✅✅✅")
    print()
    print(f"   {ok_count}/{len(bookmarks_criados)} bookmarks processados corretamente")
    print(f"   - Todos com cloud_thumbnail_url → Supabase Storage")
    print(f"   - Todos com metadata.thumbnail_url → Instagram CDN original")
    print()
    print(f"🎉 DEU TUDO CERTO! Correção validada!")
    print(f"🚀 Pode prosseguir com migração completa!")
elif ok_count >= len(bookmarks_criados) * 0.9:  # 90% ou mais
    print(f"✅ TESTE QUASE PERFEITO: {ok_count}/{len(bookmarks_criados)} OK ({int(ok_count/len(bookmarks_criados)*100)}%)")
    print()
    print(f"Problemas encontrados ({fail_count}):")
    for issue in issues:
        print(f"   - {issue}")
else:
    print(f"⚠️  TESTE PARCIAL: {ok_count}/{len(bookmarks_criados)} OK ({int(ok_count/len(bookmarks_criados)*100)}%)")
    print()
    print(f"Problemas encontrados ({fail_count}):")
    for issue in issues[:10]:  # Mostrar só os 10 primeiros
        print(f"   - {issue}")
    if len(issues) > 10:
        print(f"   ... e mais {len(issues) - 10} problemas")

print()
print("=" * 80)
print("📝 ATUALIZANDO CSV COM RESULTADOS")
print("=" * 80)
print()

# Atualizar CSV
from datetime import datetime
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for bm in bookmarks_criados:
    result = supabase.table('bookmarks').select('processing_status').eq('id', bm['bookmark_id']).single().execute()
    if result.data['processing_status'] == 'completed':
        for row in rows:
            if row['ID'] == bm['csv_id']:
                row['migrado'] = 'SIM'
                row['data_migracao'] = now
                break

with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ CSV atualizado")
print()
print("=" * 80)
