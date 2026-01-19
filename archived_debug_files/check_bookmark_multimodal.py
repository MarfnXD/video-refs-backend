"""
Script para verificar se os dados multimodais foram salvos no Supabase
para o bookmark 38d1be33-a3d4-4961-9cb0-e945a04036ab
"""
import os
from supabase import create_client, Client

# Supabase config
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bookmark_id = "38d1be33-a3d4-4961-9cb0-e945a04036ab"

print("=" * 80)
print(f"🔍 Consultando bookmark no Supabase: {bookmark_id}")
print("=" * 80)

try:
    response = supabase.table("bookmarks").select(
        "id, title, url, video_transcript, visual_analysis, transcript_language, analyzed_at, local_video_path, cloud_video_url"
    ).eq("id", bookmark_id).execute()

    if not response.data:
        print(f"\n❌ Bookmark NÃO ENCONTRADO: {bookmark_id}")
    else:
        bookmark = response.data[0]
        print(f"\n✅ Bookmark ENCONTRADO")
        print(f"   📌 Título: {bookmark['title'][:80]}...")
        print(f"   🔗 URL: {bookmark['url']}")
        print(f"   📁 Local video path: {bookmark['local_video_path']}")
        print(f"   ☁️ Cloud video URL: {bookmark['cloud_video_url'][:50] if bookmark['cloud_video_url'] else 'N/A'}...")
        print(f"\n🎬 ANÁLISE MULTIMODAL:")
        print(f"   🎤 video_transcript: {'SIM' if bookmark['video_transcript'] else 'NÃO'} ({len(bookmark['video_transcript']) if bookmark['video_transcript'] else 0} chars)")
        print(f"   👁️ visual_analysis: {'SIM' if bookmark['visual_analysis'] else 'NÃO'} ({len(bookmark['visual_analysis']) if bookmark['visual_analysis'] else 0} chars)")
        print(f"   🌐 transcript_language: {bookmark['transcript_language'] or 'N/A'}")
        print(f"   📅 analyzed_at: {bookmark['analyzed_at'] or 'N/A'}")

        if bookmark['video_transcript']:
            print(f"\n📝 TRANSCRIÇÃO (primeiros 200 chars):")
            print(f"   {bookmark['video_transcript'][:200]}...")

        if bookmark['visual_analysis']:
            print(f"\n🖼️ ANÁLISE VISUAL (primeiros 200 chars):")
            print(f"   {bookmark['visual_analysis'][:200]}...")

except Exception as e:
    print(f"\n❌ ERRO ao consultar Supabase: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ Consulta concluída")
print("=" * 80)
