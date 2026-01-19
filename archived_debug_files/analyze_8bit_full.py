"""
Análise completa dos dados do bookmark "Until I Find You"
para entender por que a IA gerou tags/categorias erradas
"""
import requests
import json

SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

bookmark_id = "38d1be33-a3d4-4961-9cb0-e945a04036ab"

print("="*100)
print(f"🔍 ANÁLISE COMPLETA DO BOOKMARK")
print("="*100)

url = f"{SUPABASE_URL}/rest/v1/bookmarks"
params = {
    "id": f"eq.{bookmark_id}",
    "select": "*"
}
headers = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(url, params=params, headers=headers)

if response.status_code != 200:
    print(f"\n❌ Erro HTTP {response.status_code}: {response.text}")
    exit(1)

data = response.json()
if not data:
    print(f"\n❌ Bookmark NÃO ENCONTRADO")
    exit(1)

bookmark = data[0]
metadata = bookmark.get('metadata', {})

print(f"\n📌 TÍTULO ORIGINAL:")
print(f"   {bookmark.get('title', 'N/A')}")

print(f"\n📝 DESCRIÇÃO (metadata):")
description = metadata.get('description', 'N/A')
print(f"   {description[:300] if description and description != 'N/A' else 'N/A'}...")

print(f"\n🏷️ HASHTAGS:")
hashtags = metadata.get('hashtags', [])
if hashtags:
    print(f"   {', '.join(hashtags)}")
else:
    print("   (Nenhuma hashtag)")

print(f"\n💬 COMENTÁRIOS FILTRADOS ({len(bookmark.get('filtered_comments', []))}):")
filtered_comments = bookmark.get('filtered_comments', [])
if filtered_comments:
    for i, comment in enumerate(filtered_comments[:15], 1):  # Mostra até 15
        text = comment.get('text', '')
        likes = comment.get('likes', 0)
        print(f"   {i}. [{likes} likes] {text[:80]}")
else:
    print("   (Nenhum comentário)")

print(f"\n🎤 TRANSCRIÇÃO (Whisper):")
transcript = bookmark.get('video_transcript', '')
if transcript:
    print(f"   Idioma: {bookmark.get('transcript_language', 'N/A')}")
    print(f"   Conteúdo: {transcript}")
else:
    print("   (Nenhuma transcrição)")

print(f"\n👁️ ANÁLISE VISUAL (GPT-4 Vision):")
visual = bookmark.get('visual_analysis', '')
if visual:
    print(f"   {visual}")
else:
    print("   (Nenhuma análise visual)")

print(f"\n" + "="*100)
print(f"🤖 ANÁLISE GERADA PELA IA (Claude)")
print("="*100)

print(f"\n✨ AUTO DESCRIPTION:")
auto_desc = bookmark.get('auto_description', 'N/A')
print(f"   {auto_desc}")

print(f"\n🏷️ AUTO TAGS:")
auto_tags = bookmark.get('auto_tags', [])
if auto_tags:
    print(f"   {', '.join(auto_tags)}")
else:
    print("   (Nenhuma tag gerada)")

print(f"\n📁 AUTO CATEGORIES:")
auto_cats = bookmark.get('auto_categories', [])
if auto_cats:
    print(f"   {', '.join(auto_cats)}")
else:
    print("   (Nenhuma categoria gerada)")

print(f"\n⭐ RELEVANCE SCORE:")
print(f"   {bookmark.get('relevance_score', 'N/A')}")

print("\n" + "="*100)
print("✅ Análise concluída")
print("="*100)
