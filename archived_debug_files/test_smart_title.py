"""
Script de teste para validar geração de Smart Titles
"""
import os
from dotenv import load_dotenv
from supabase import create_client
import requests
import time

load_dotenv()

# Configuração
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = os.getenv('BACKEND_URL', 'https://video-refs-backend.onrender.com')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

# URL de teste (vídeo Instagram com título clickbait)
TEST_URL = 'https://www.instagram.com/reel/DCXInoBSICF/'

print("🧪 TESTE DE SMART TITLES")
print("=" * 60)
print(f"URL de teste: {TEST_URL}")
print(f"Backend: {BACKEND_URL}")
print()

# Conectar ao Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Deletar bookmark se já existe
print("🗑️ Limpando bookmark anterior (se existir)...")
supabase.table('bookmarks').delete().eq('url', TEST_URL).eq('user_id', USER_ID).execute()
print("✓ Limpeza concluída")
print()

# 2. Criar novo bookmark
print("📝 Criando novo bookmark...")
result = supabase.table('bookmarks').insert({
    'url': TEST_URL,
    'user_id': USER_ID,
    'processing_status': 'pending'
}).execute()

bookmark_id = result.data[0]['id']
print(f"✓ Bookmark criado: {bookmark_id}")
print()

# 3. Enfileirar para processamento
print("⚙️ Enfileirando processamento...")
response = requests.post(f'{BACKEND_URL}/api/process-bookmark-complete', json={
    'bookmark_id': bookmark_id,
    'user_id': USER_ID,
    'url': TEST_URL
})

if response.status_code == 200:
    job_data = response.json()
    print(f"✓ Job enfileirado: {job_data.get('job_id')}")
    print(f"  Tempo estimado: {job_data.get('estimated_time_seconds', 'N/A')}s")
else:
    print(f"❌ Erro ao enfileirar: {response.status_code}")
    print(response.text)
    exit(1)

print()
print("⏰ Aguardando processamento completar...")
print("   (máximo 5 minutos)")
print()

# 4. Monitorar processamento
for i in range(20):  # 20 verificações x 15s = 5 minutos max
    time.sleep(15)

    result = supabase.table('bookmarks').select('processing_status, error_message').eq('id', bookmark_id).execute()

    if result.data:
        status = result.data[0]['processing_status']
        error = result.data[0].get('error_message', '')

        status_emoji = {
            'pending': '⏸️',
            'queued': '⏳',
            'processing': '⚙️',
            'completed': '✅',
            'failed': '❌'
        }.get(status, '❓')

        print(f"[{i+1}/20] {status_emoji} {status}")

        if status == 'completed':
            print()
            print("🎉 PROCESSAMENTO COMPLETADO!")
            break
        elif status == 'failed':
            print()
            print(f"❌ FALHOU: {error}")
            exit(1)

print()
print("=" * 60)

# 5. Buscar resultado
result = supabase.table('bookmarks').select('title, smart_title, auto_tags, auto_categories, auto_description').eq('id', bookmark_id).execute()

if result.data:
    bm = result.data[0]

    print("📊 RESULTADO DO TESTE:")
    print()
    print("❌ Título original (clickbait):")
    print(f"   {bm.get('title', 'N/A')}")
    print()

    if bm.get('smart_title'):
        print("✅ Smart title (descritivo):")
        print(f"   {bm['smart_title']}")
        print()
        print(f"   Tamanho: {len(bm['smart_title'])} caracteres")
        print()
    else:
        print("⚠️ Smart title NÃO foi gerado!")
        print()

    print("🏷️ Tags automáticas:")
    tags = bm.get('auto_tags', [])
    if tags:
        print(f"   {', '.join(tags[:10])}")
    else:
        print("   (nenhuma)")
    print()

    print("📁 Categorias automáticas:")
    categories = bm.get('auto_categories', [])
    if categories:
        print(f"   {', '.join(categories)}")
    else:
        print("   (nenhuma)")
    print()

    print("📝 Descrição automática:")
    desc = bm.get('auto_description', '')
    if desc:
        print(f"   {desc[:150]}{'...' if len(desc) > 150 else ''}")
    else:
        print("   (nenhuma)")

    print()
    print("=" * 60)

    # Resultado final
    if bm.get('smart_title'):
        print("✅ TESTE PASSOU - Smart Title foi gerado com sucesso!")
    else:
        print("❌ TESTE FALHOU - Smart Title não foi gerado")
else:
    print("❌ Erro ao buscar bookmark")
