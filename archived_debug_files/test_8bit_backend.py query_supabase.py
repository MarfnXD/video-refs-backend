import requests
import json

SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

bookmark_id = "38d1be33-a3d4-4961-9cb0-e945a04036ab"

print("="*80)
print(f"🔍 Consultando bookmark: {bookmark_id}")
print("="*80)

url = f"{SUPABASE_URL}/rest/v1/bookmarks"
params = {
    "id": f"eq.{bookmark_id}",
    "select": "id,title,url,video_transcript,visual_analysis,transcript_language,analyzed_at,local_video_path,cloud_video_url"
}
headers = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    if not data:
        print(f"\n❌ Bookmark NÃO ENCONTRADO")
    else:
        bookmark = data[0]
        print(f"\n✅ Bookmark ENCONTRADO")
        print(f"   📌 Título: {bookmark['title'][:80] if bookmark['title'] else 'N/A'}...")
        print(f"   🔗 URL: {bookmark['url'][:60]}...")
        print(f"   📁 Local video: {bookmark['local_video_path'] or 'N/A'}")
        print(f"   ☁️ Cloud video: {'SIM' if bookmark['cloud_video_url'] else 'NÃO'}")
        print(f"\n🎬 ANÁLISE MULTIMODAL:")
        transcript = bookmark.get('video_transcript')
        analysis = bookmark.get('visual_analysis')
        print(f"   🎤 video_transcript: {'SIM' if transcript else 'NÃO'} ({len(transcript) if transcript else 0} chars)")
        print(f"   👁️ visual_analysis: {'SIM' if analysis else 'NÃO'} ({len(analysis) if analysis else 0} chars)")
        print(f"   🌐 transcript_language: {bookmark.get('transcript_language') or 'N/A'}")
        print(f"   📅 analyzed_at: {bookmark.get('analyzed_at') or 'N/A'}")

        if transcript:
            print(f"\n📝 TRANSCRIÇÃO (primeiros 150 chars):")
            print(f"   {transcript[:150]}...")

        if analysis:
            print(f"\n🖼️ ANÁLISE VISUAL (primeiros 150 chars):")
            print(f"   {analysis[:150]}...")
else:
    print(f"\n❌ Erro HTTP {response.status_code}: {response.text}")

print("\n" + "="*80)
print("✅ Consulta concluída")
print("="*80)
