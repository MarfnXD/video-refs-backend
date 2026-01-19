"""
Testa 2 bookmarks e mostra instruções para coletar logs detalhados
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
print("🧪 TESTE COM 2 BOOKMARKS + LOGS DETALHADOS")
print("=" * 80)
print()

# Deletar bookmarks de testes anteriores
print("🗑️  Limpando bookmarks de testes anteriores...")
result = supabase.table('bookmarks').select('id').eq('user_id', USER_ID).order('created_at', desc=True).limit(10).execute()
if result.data:
    for bm in result.data:
        supabase.table('bookmarks').delete().eq('id', bm['id']).execute()
    print(f"✅ {len(result.data)} bookmarks deletados")
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
print(f"⏳ AGUARDANDO PROCESSAMENTO (max 2 minutos)")
print("=" * 80)
print()

max_wait = 120
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
print("📋 BOOKMARKS CRIADOS:")
print("=" * 80)
print()

for bm in bookmarks_criados:
    print(f"CSV ID {bm['csv_id']}: {bm['bookmark_id']}")
print()

print("=" * 80)
print("📝 INSTRUÇÕES PARA COLETAR LOGS:")
print("=" * 80)
print()
print("1. Acesse: https://dashboard.render.com")
print("2. Abra o serviço 'video-refs-backend'")
print("3. Vá na aba 'Logs'")
print("4. Use a busca e procure por:")
print()
print(f"   Para cada bookmark acima, procure:")
for bm in bookmarks_criados:
    short_id = bm['bookmark_id'][:8]
    print(f"   - '{short_id}' OU '[BACKGROUND_PROCESSOR]'")
print()
print("5. Procure especificamente por estas linhas (com emojis):")
print("   🔍 [BACKGROUND_PROCESSOR] METADATA ANTES DE UPLOAD:")
print("   📸 [BACKGROUND_PROCESSOR] Chamando ThumbnailService.upload_thumbnail()")
print("   🔍 [BACKGROUND_PROCESSOR] METADATA DEPOIS DE UPLOAD:")
print("   💾 [BACKGROUND_PROCESSOR] DADOS QUE SERÃO SALVOS:")
print()
print("6. Copie TODAS as linhas com esses emojis e cole aqui no chat")
print()
print("=" * 80)
print()
print("⚠️  IMPORTANTE: Precisamos dos logs dos 2 bookmarks para comparar")
print("   um que funciona vs um que falha!")
print()
print("=" * 80)
