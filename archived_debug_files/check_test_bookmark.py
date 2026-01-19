"""
Verifica status do bookmark de teste
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

BOOKMARK_ID = '887430ad-9355-4d65-9fa8-cd67ef6cf9e0'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

result = supabase.table('bookmarks').select('*').eq('id', BOOKMARK_ID).single().execute()
bookmark = result.data

print("=" * 80)
print("STATUS DO BOOKMARK DE TESTE")
print("=" * 80)
print()
print(f"ID: {BOOKMARK_ID}")
print(f"Status: {bookmark.get('processing_status')}")
print(f"Error: {bookmark.get('error_message')}")
print()
print(f"Metadata: {'✅' if bookmark.get('metadata') else '❌'}")
print(f"cloud_thumbnail_url: {'✅' if bookmark.get('cloud_thumbnail_url') else '❌'}")
print(f"cloud_video_url: {'✅' if bookmark.get('cloud_video_url') else '❌'}")
print(f"video_transcript: {'✅' if bookmark.get('video_transcript') else '❌'}")
print(f"visual_analysis: {'✅' if bookmark.get('visual_analysis') else '❌'}")
print(f"smart_title: {'✅' if bookmark.get('smart_title') else '❌'}")
print()

if bookmark.get('metadata'):
    metadata = bookmark['metadata']
    print("Metadata.thumbnail_url:")
    thumb = metadata.get('thumbnail_url')
    if thumb:
        if 'cdninstagram' in thumb or 'instagram' in thumb:
            print(f"✅ Instagram CDN: {thumb[:80]}...")
        elif 'supabase' in thumb.lower():
            print(f"❌ CORROMPIDA (Supabase): {thumb[:80]}...")
        else:
            print(f"⚠️  Desconhecida: {thumb[:80]}...")
    else:
        print("❌ NULL")

print("=" * 80)
