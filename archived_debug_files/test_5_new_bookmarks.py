"""
Testa processamento de 5 novos bookmarks para validar correção
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
print("🧪 TESTE - 5 NOVOS BOOKMARKS (Validar Correção)")
print("=" * 80)
print()

# Pegar 5 URLs não migradas do CSV
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    nao_migradas = [row for row in reader if row['migrado'] == 'NÃO']

urls_teste = nao_migradas[:5]

print(f"URLs selecionadas do CSV:")
for row in urls_teste:
    print(f"  ID {row['ID']}: {row['URL'][:60]}...")
print()

# Criar e enfileirar
bookmarks_criados = []

for row in urls_teste:
    url = row['URL']
    csv_id = row['ID']

    print(f"[{csv_id}] Processando: {url[:60]}...")

    # Verificar se já existe
    existing = supabase.table('bookmarks').select('id').eq('url', url).eq('user_id', USER_ID).execute()
    if existing.data:
        print(f"  ⚠️  Já existe, deletando...")
        supabase.table('bookmarks').delete().eq('id', existing.data[0]['id']).execute()

    # Criar
    result = supabase.table('bookmarks').insert({
        'user_id': USER_ID,
        'url': url,
        'processing_status': 'pending'
    }).execute()

    bookmark_id = result.data[0]['id']
    print(f"  ✅ Criado: {bookmark_id[:8]}...")

    # Enfileirar
    response = requests.post(
        'https://video-refs-backend.onrender.com/api/process-bookmark-complete',
        json={
            'bookmark_id': bookmark_id,
            'url': url,
            'user_id': USER_ID,
            'upload_to_cloud': True,
            'analyze_video': False  # Desabilitar Gemini para ser mais rápido
        }
    )

    if response.status_code == 200:
        print(f"  ✅ Enfileirado")
        bookmarks_criados.append({
            'csv_id': csv_id,
            'bookmark_id': bookmark_id,
            'url': url
        })
    else:
        print(f"  ❌ Erro ao enfileirar: {response.status_code}")

    print()

print("=" * 80)
print(f"⏳ AGUARDANDO PROCESSAMENTO (max 3 minutos)")
print("=" * 80)
print()

max_wait = 180
start_time = time.time()

while (time.time() - start_time) < max_wait:
    # Verificar status de todos
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

sucessos = 0
falhas = 0
problemas = []

for bm in bookmarks_criados:
    result = supabase.table('bookmarks').select('*').eq('id', bm['bookmark_id']).single().execute()
    bookmark = result.data

    print(f"[CSV ID {bm['csv_id']}] {bm['url'][:50]}...")
    print(f"  Bookmark ID: {bm['bookmark_id'][:8]}...")
    print(f"  Status: {bookmark.get('processing_status')}")

    if bookmark.get('processing_status') == 'completed':
        metadata = bookmark.get('metadata') or {}
        cloud_thumb = bookmark.get('cloud_thumbnail_url')
        thumb_meta = metadata.get('thumbnail_url')

        # Validar campos críticos
        issues = []

        if not cloud_thumb:
            issues.append("cloud_thumbnail_url NULL")
        elif 'supabase' not in cloud_thumb.lower():
            issues.append("cloud_thumbnail_url não é do Supabase")

        if not thumb_meta:
            issues.append("metadata.thumbnail_url NULL")
        elif 'instagram' not in thumb_meta and 'cdninstagram' not in thumb_meta:
            if 'supabase' in thumb_meta.lower():
                issues.append("⚠️ CRÍTICO: metadata.thumbnail_url corrompida (Supabase)")
            else:
                issues.append("metadata.thumbnail_url não é do Instagram CDN")

        if issues:
            print(f"  ❌ Problemas:")
            for issue in issues:
                print(f"     - {issue}")
            falhas += 1
            problemas.extend(issues)
        else:
            print(f"  ✅ Todos os campos OK!")
            print(f"     - cloud_thumbnail_url: Supabase")
            print(f"     - metadata.thumbnail_url: Instagram CDN")
            sucessos += 1

    else:
        print(f"  ❌ Não completou: {bookmark.get('error_message', 'Sem erro')}")
        falhas += 1

    print()

print("=" * 80)
print("📊 RESULTADO FINAL")
print("=" * 80)
print()
print(f"✅ Sucessos: {sucessos}/{len(bookmarks_criados)}")
print(f"❌ Falhas: {falhas}/{len(bookmarks_criados)}")
print()

if sucessos == len(bookmarks_criados):
    print(f"🎉 TESTE 100% APROVADO!")
    print(f"   Correção do bug de double upload validada!")
    print()
    print(f"✅ Pode prosseguir com migração completa dos {len(nao_migradas)} bookmarks restantes")
elif sucessos > 0:
    print(f"⚠️  TESTE PARCIALMENTE APROVADO")
    print(f"   {sucessos} bookmarks OK, {falhas} com problemas")
    print()
    print(f"Problemas encontrados:")
    for prob in set(problemas):
        print(f"   - {prob}")
else:
    print(f"❌ TESTE FALHOU")
    print(f"   Nenhum bookmark processado corretamente")
    print()
    print(f"⚠️  NÃO prosseguir com migração até resolver problemas")

print()
print("=" * 80)

# Atualizar CSV
print()
print("Atualizando CSV...")
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

from datetime import datetime
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

for bm in bookmarks_criados:
    for row in rows:
        if row['ID'] == bm['csv_id']:
            row['migrado'] = 'SIM'
            row['data_migracao'] = now
            break

with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ CSV atualizado com {len(bookmarks_criados)} URLs marcadas como migradas")
print()
print("=" * 80)
