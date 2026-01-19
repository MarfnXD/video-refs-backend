"""
Verifica bookmarks em processing
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
print("BOOKMARKS EM PROCESSING")
print("=" * 80)
print()

result = supabase.table('bookmarks')\
    .select('id, url, processing_status, processing_started_at, created_at')\
    .eq('user_id', USER_ID)\
    .eq('processing_status', 'processing')\
    .order('processing_started_at', desc=True)\
    .execute()

processing = result.data or []

print(f"Total em processing: {len(processing)}")
print()

if processing:
    for bm in processing:
        print(f"ID: {bm['id']}")
        print(f"URL: {bm['url'][:60]}...")
        print(f"Started: {bm.get('processing_started_at', 'NULL')}")
        print(f"Created: {bm.get('created_at', 'NULL')}")
        print()

print("=" * 80)
print()

# Verificar especificamente nosso bookmark de teste
print("BOOKMARK DE TESTE:")
print("=" * 80)
print()

test_id = '887430ad-9355-4d65-9fa8-cd67ef6cf9e0'
result = supabase.table('bookmarks').select('*').eq('id', test_id).single().execute()
test_bm = result.data

print(f"ID: {test_id}")
print(f"Status: {test_bm.get('processing_status')}")
print(f"Started: {test_bm.get('processing_started_at')}")
print(f"Completed: {test_bm.get('processing_completed_at')}")
print(f"Error: {test_bm.get('error_message')}")
print()

# Verificar o bookmark que está nos logs
print("=" * 80)
print("BOOKMARK NOS LOGS DO RENDER:")
print("=" * 80)
print()

log_id = '4a5d996b-4ac8-432c-b1f7-7beb1d3ee2ac'
try:
    result = supabase.table('bookmarks').select('*').eq('id', log_id).single().execute()
    log_bm = result.data

    print(f"ID: {log_id}")
    print(f"Status: {log_bm.get('processing_status')}")
    print(f"Started: {log_bm.get('processing_started_at')}")
    print(f"Completed: {log_bm.get('processing_completed_at')}")
    print(f"Error: {log_bm.get('error_message')}")
    print(f"URL: {log_bm.get('url')}")
except Exception as e:
    print(f"Bookmark não encontrado: {e}")

print()
print("=" * 80)
