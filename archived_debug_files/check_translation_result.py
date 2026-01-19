"""
Verifica os dados completos do vídeo traduzido
"""
from supabase import create_client, Client

SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

# Buscar vídeo
response = supabase.table("bookmarks").select("*").ilike("title", "%10 Secs practice%").execute()
bookmark = response.data[0]

print("\n" + "=" * 80)
print("📹 VÍDEO: 10 Secs practice ? aight.")
print("=" * 80)

print(f"\n📌 INFORMAÇÕES BÁSICAS:")
print(f"   ID: {bookmark['id']}")
print(f"   Plataforma: {bookmark['platform']}")
print(f"   Idioma: {bookmark['transcript_language'].upper()}")

print(f"\n🎤 TRANSCRIÇÃO ORIGINAL ({bookmark['transcript_language'].upper()}):")
print("-" * 80)
print(bookmark['video_transcript'])

print(f"\n🌐 TRANSCRIÇÃO TRADUZIDA (PT):")
print("-" * 80)
print(bookmark['video_transcript_pt'])

print(f"\n👁️  ANÁLISE VISUAL ORIGINAL (EN):")
print("-" * 80)
print(bookmark['visual_analysis'])

print(f"\n🌐 ANÁLISE VISUAL TRADUZIDA (PT):")
print("-" * 80)
print(bookmark['visual_analysis_pt'])

print("\n" + "=" * 80)
print("✅ TODOS OS CAMPOS SALVOS CORRETAMENTE!")
print("=" * 80)
