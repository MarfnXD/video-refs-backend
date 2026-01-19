"""
Teste simples: cadastrar 1 vídeo novo e verificar thumbnail
"""
import os
import requests
import time
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("TESTE DE THUMBNAIL - 1 VÍDEO")
print("=" * 80)
print()

# 1 URL de teste (nova, não cadastrada)
test_url = 'https://www.instagram.com/reel/DGbQZgzxvHF/'  # Teste 2

print(f"📝 URL: {test_url}")
print()

# Criar bookmark
bookmark_data = {
    'url': test_url,
    'title': 'Teste Thumbnail Upload',
    'platform': 'instagram',
    'user_id': USER_ID,
    'processing_status': 'queued',
}

result = supabase.table('bookmarks').insert(bookmark_data).execute()
bookmark_id = result.data[0]['id']

print(f"✅ Bookmark criado: {bookmark_id}")
print()

# Chamar backend (SÓ METADADOS - sem IA)
print("🚀 Enviando para processamento (só metadados)...")
response = requests.post(
    f'{BACKEND_URL}/api/process-bookmark-complete',
    json={
        'bookmark_id': bookmark_id,
        'url': test_url,
        'user_id': USER_ID,
        'extract_metadata': True,
        'analyze_video': False,
        'process_ai': False,
        'upload_to_cloud': False,
        'user_context': None,
    },
    timeout=120
)

if response.status_code == 200:
    job_data = response.json()
    job_id = job_data.get('job_id', 'N/A')[:8]
    print(f"✅ Enfileirado: job {job_id}...")
else:
    print(f"❌ Erro HTTP: {response.status_code}")
    exit(1)

print()
print("⏳ Aguardando 45 segundos para processamento...")
time.sleep(45)

# Verificar resultado
print()
print("=" * 80)
print("📊 RESULTADO")
print("=" * 80)
print()

result = supabase.table('bookmarks') \
    .select('id, processing_status, cloud_thumbnail_url, thumbnail, error_message') \
    .eq('id', bookmark_id) \
    .execute()

if result.data:
    bm = result.data[0]
    status = bm['processing_status']
    cloud_thumb = bm.get('cloud_thumbnail_url')
    thumb = bm.get('thumbnail')
    error = bm.get('error_message')

    print(f"Status: {status}")
    print()

    if error:
        print(f"❌ ERRO: {error}")
        print()

    if thumb:
        print(f"Thumbnail original (Instagram):")
        print(f"  {thumb}")
        print()

    if cloud_thumb:
        is_supabase = 'supabase.co' in cloud_thumb
        is_instagram = 'instagram.com' in cloud_thumb or 'cdninstagram.com' in cloud_thumb

        print(f"Cloud Thumbnail URL:")
        print(f"  {cloud_thumb}")
        print()

        if is_supabase:
            print("✅ ✅ ✅ SUCESSO! Thumbnail salva no Supabase Storage!")
            print()
            print("🎉 O upload de thumbnails está funcionando corretamente!")
        elif is_instagram:
            print("❌ ❌ ❌ FALHA! Thumbnail ainda aponta para Instagram CDN!")
            print()
            print("⚠️  O upload não está funcionando. Precisa investigar.")
        else:
            print(f"⚠️  Domínio desconhecido")
    else:
        print("⚠️  Cloud Thumbnail: N/A")
        print()
        if status == 'processing':
            print("⏳ Ainda processando. Aguarde mais um pouco e execute:")
            print(f"   python check_test_videos.py")

print()
print(f"📝 Bookmark ID: {bookmark_id}")
