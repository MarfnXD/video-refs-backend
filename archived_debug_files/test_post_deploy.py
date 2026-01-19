"""
Testa processamento APÓS o deploy da correção
"""
import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

# Nova URL de teste (do CSV, não migrada ainda)
TEST_URL = "https://www.instagram.com/reel/DFxa4siJJyp/"  # ID 76 do CSV

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🧪 TESTE PÓS-DEPLOY - Validar Correção")
print("=" * 80)
print()

# Verificar se URL já existe
print(f"Verificando se URL já existe...")
existing = supabase.table('bookmarks').select('id').eq('url', TEST_URL).eq('user_id', USER_ID).execute()
if existing.data:
    print(f"❌ URL já existe! Deletando...")
    supabase.table('bookmarks').delete().eq('id', existing.data[0]['id']).execute()
    print(f"✅ Deletado")

print()

# Criar bookmark
print(f"Criando bookmark...")
print(f"URL: {TEST_URL}")

result = supabase.table('bookmarks').insert({
    'user_id': USER_ID,
    'url': TEST_URL,
    'processing_status': 'pending'
}).execute()

bookmark_id = result.data[0]['id']
print(f"✅ Criado: {bookmark_id}")
print()

# Enfileirar
print(f"Enfileirando processamento completo...")
response = requests.post(
    'https://video-refs-backend.onrender.com/api/process-bookmark-complete',
    json={
        'bookmark_id': bookmark_id,
        'url': TEST_URL,
        'user_id': USER_ID,
        'upload_to_cloud': True,
        'analyze_video': False  # Desabilitar Gemini para ser mais rápido
    }
)

if response.status_code == 200:
    print(f"✅ Enfileirado")
else:
    print(f"❌ Erro: {response.status_code} - {response.text}")
    exit(1)

print()

# Aguardar
print(f"⏳ Aguardando processamento (max 2 minutos)...")
print()

max_wait = 120
start_time = time.time()

while (time.time() - start_time) < max_wait:
    result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()
    bm = result.data
    status = bm.get('processing_status')

    if status == 'completed':
        print(f"✅ Processamento completo!")
        break
    elif status == 'failed':
        print(f"❌ Processamento falhou: {bm.get('error_message')}")
        exit(1)
    else:
        elapsed = int(time.time() - start_time)
        print(f"   Status: {status} ({elapsed}s)", end='\r')
        time.sleep(3)

print()
print()

# Validar
print("=" * 80)
print("🔍 VALIDAÇÃO")
print("=" * 80)
print()

metadata = bm.get('metadata') or {}
cloud_thumb = bm.get('cloud_thumbnail_url')
thumb_meta = metadata.get('thumbnail_url')

print(f"1️⃣ cloud_thumbnail_url (campo da tabela):")
if cloud_thumb and 'supabase' in cloud_thumb.lower():
    print(f"   ✅ {cloud_thumb[:70]}...")
else:
    print(f"   ❌ {cloud_thumb or 'NULL'}")

print()

print(f"2️⃣ metadata.thumbnail_url:")
if thumb_meta:
    if 'instagram' in thumb_meta or 'cdninstagram' in thumb_meta:
        print(f"   ✅ {thumb_meta[:70]}...")
        print(f"   🎉 CORREÇÃO FUNCIONOU! Instagram CDN preservada!")
    elif 'supabase' in thumb_meta.lower():
        print(f"   ❌ {thumb_meta[:70]}...")
        print(f"   ❌ BUG AINDA PRESENTE")
    else:
        print(f"   ⚠️  {thumb_meta[:70]}...")
else:
    print(f"   ❌ NULL")

print()
print("=" * 80)
print()

if thumb_meta and ('instagram' in thumb_meta or 'cdninstagram' in thumb_meta):
    print(f"✅ TESTE PASSOU! Correção validada!")
    print(f"   Bookmark ID: {bookmark_id}")
else:
    print(f"❌ TESTE FALHOU! Bug ainda presente ou metadados não extraídos.")
    print(f"   Bookmark ID: {bookmark_id}")

print()
print("=" * 80)
