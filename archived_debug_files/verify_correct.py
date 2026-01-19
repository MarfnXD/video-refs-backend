"""
Verifica os bookmarks usando o nome CORRETO do campo: cloud_thumbnail_url
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# IDs dos bookmarks criados no teste
bookmark_ids = [
    '9d0a8bf8-3006-4c99-9b02-1b4b11cd1c5f',
    'eefc288c-655a-4abb-b1c7-ac79460d3cf6',
    '88788190-2bf6-474c-9391-60bc63c6c8ec',
    'f49ad048-d3b8-4669-b3f8-113c66a382f5',
    'a040b835-1d19-4d7f-ae17-0d52a024e7ce'  # Do timeout
]

print("=" * 80)
print("🔍 VERIFICAÇÃO CORRIGIDA (cloud_thumbnail_url)")
print("=" * 80)
print()

all_ok = True

for idx, bookmark_id in enumerate(bookmark_ids, 1):
    print(f"📋 [{idx}/{len(bookmark_ids)}] {bookmark_id}")

    result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()

    if not result.data:
        print(f"  ❌ Não encontrado")
        all_ok = False
        print()
        continue

    data = result.data

    # CAMPO CORRETO: cloud_thumbnail_url (não cloud_thumb_url)
    processing_status = data.get('processing_status')
    cloud_video_url = data.get('cloud_video_url')
    cloud_thumbnail_url = data.get('cloud_thumbnail_url')  # ✅ NOME CORRETO
    smart_title = data.get('smart_title')
    gemini_analysis = data.get('gemini_analysis')

    print(f"  Status: {processing_status}")
    print(f"  Title: {smart_title[:50] if smart_title else 'NULL'}...")
    print()

    # Verificações
    errors = []

    if not cloud_video_url:
        errors.append("cloud_video_url NULL")
    elif 'supabase' not in cloud_video_url.lower():
        errors.append("cloud_video_url não é Supabase")

    if not cloud_thumbnail_url:
        errors.append("cloud_thumbnail_url NULL")
    elif 'supabase' not in cloud_thumbnail_url.lower():
        errors.append("cloud_thumbnail_url não é Supabase")

    if not gemini_analysis:
        errors.append("gemini_analysis NULL")

    if errors:
        print(f"  ❌ Problemas:")
        for error in errors:
            print(f"     - {error}")
        all_ok = False
    else:
        print(f"  ✅ TUDO OK!")
        print(f"     cloud_video_url: ✅")
        print(f"     cloud_thumbnail_url: ✅")
        print(f"     gemini_analysis: ✅")

    print()
    print("-" * 80)
    print()

print()
print("=" * 80)
if all_ok:
    print("🎉 TODOS OS BOOKMARKS ESTÃO PERFEITOS!")
    print("✅ Pode rodar a migração completa.")
else:
    print("⚠️  Alguns bookmarks ainda têm problemas.")
print("=" * 80)
