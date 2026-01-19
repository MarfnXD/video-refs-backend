"""
Reseta o bookmark de teste e reenfileira
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

BOOKMARK_ID = '887430ad-9355-4d65-9fa8-cd67ef6cf9e0'
TEST_URL = "https://www.instagram.com/reel/DBeO5RoOBx5/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("RESETANDO BOOKMARK DE TESTE")
print("=" * 80)
print()

# 1. Resetar status para pending
print(f"1. Resetando status para pending...")
supabase.table('bookmarks').update({
    'processing_status': 'pending',
    'processing_started_at': None,
    'processing_completed_at': None,
    'error_message': None
}).eq('id', BOOKMARK_ID).execute()
print(f"✅ Status resetado")
print()

# 2. Reenfileirar processamento
print(f"2. Reenfileirando processamento...")
response = requests.post(
    'https://video-refs-backend.onrender.com/api/process-bookmark-complete',
    json={
        'bookmark_id': BOOKMARK_ID,
        'url': TEST_URL,
        'user_id': USER_ID,
        'upload_to_cloud': True,
        'analyze_video': True
    }
)

if response.status_code == 200:
    print(f"✅ Processamento reenfileirado com sucesso")
    print(f"   Response: {response.json()}")
else:
    print(f"❌ Erro ao reenfileirar: {response.status_code}")
    print(f"   {response.text}")

print()
print("=" * 80)
print()
print(f"Bookmark ID: {BOOKMARK_ID}")
print(f"Aguarde ~2-3 minutos e rode: python check_test_bookmark.py")
print()
print("=" * 80)
