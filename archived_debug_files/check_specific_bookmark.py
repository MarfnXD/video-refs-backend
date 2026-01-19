"""
Verifica o bookmark específico que apareceu nos logs do Render
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bookmark que apareceu nos logs do Render
bookmark_id = 'a040b835-1d19-4d7f-ae17-0d52a024e7ce'

print("=" * 80)
print(f"🔍 Verificando bookmark: {bookmark_id}")
print("=" * 80)
print()

result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()

if not result.data:
    print("❌ Bookmark não encontrado!")
else:
    data = result.data

    print(f"Status: {data.get('processing_status')}")
    print(f"Smart Title: {data.get('smart_title')}")
    print()
    print(f"cloud_video_url: {data.get('cloud_video_url')}")
    print()
    print(f"cloud_thumb_url: {data.get('cloud_thumb_url')}")
    print()
    print(f"thumbnail_url (Instagram): {data.get('thumbnail_url')}")
    print()
    print(f"gemini_analysis: {'OK' if data.get('gemini_analysis') else 'NULL'}")
    if data.get('gemini_analysis'):
        print(f"  Preview: {str(data.get('gemini_analysis'))[:200]}...")
    print()
    print(f"claude_analysis: {'OK' if data.get('claude_analysis') else 'NULL'}")
    print()

    # Verificar se está tudo OK
    has_cloud_thumb = bool(data.get('cloud_thumb_url'))
    has_gemini = bool(data.get('gemini_analysis'))

    print("=" * 80)
    if has_cloud_thumb and has_gemini:
        print("✅ TUDO OK! Backend está salvando corretamente.")
    else:
        print("⚠️  Ainda faltando:")
        if not has_cloud_thumb:
            print("  - cloud_thumb_url")
        if not has_gemini:
            print("  - gemini_analysis")
