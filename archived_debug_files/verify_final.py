"""
Verificação FINAL com os nomes CORRETOS dos campos
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

bookmark_ids = [
    '9d0a8bf8-3006-4c99-9b02-1b4b11cd1c5f',
    'eefc288c-655a-4abb-b1c7-ac79460d3cf6',
    '88788190-2bf6-474c-9391-60bc63c6c8ec',
    'f49ad048-d3b8-4669-b3f8-113c66a382f5',
    'a040b835-1d19-4d7f-ae17-0d52a024e7ce'
]

print("=" * 80)
print("🔍 VERIFICAÇÃO FINAL - Campos Corretos")
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

    # Campos corretos
    processing_status = data.get('processing_status')
    cloud_video_url = data.get('cloud_video_url')
    cloud_thumbnail_url = data.get('cloud_thumbnail_url')  # ✅ Correto
    smart_title = data.get('smart_title')
    
    # Gemini salva nesses campos (não em gemini_analysis)
    video_transcript = data.get('video_transcript')  # ✅ Correto
    visual_analysis = data.get('visual_analysis')    # ✅ Correto

    print(f"  Status: {processing_status}")
    print(f"  Title: {smart_title[:50] if smart_title else 'NULL'}...")
    print()

    # Verificações
    errors = []

    if not cloud_video_url or 'supabase' not in cloud_video_url.lower():
        errors.append("cloud_video_url")

    if not cloud_thumbnail_url or 'supabase' not in cloud_thumbnail_url.lower():
        errors.append("cloud_thumbnail_url")

    if not video_transcript:
        errors.append("video_transcript (Gemini)")

    if not visual_analysis:
        errors.append("visual_analysis (Gemini)")

    if not smart_title:
        errors.append("smart_title")

    if errors:
        print(f"  ❌ Faltando: {', '.join(errors)}")
        all_ok = False
    else:
        print(f"  ✅ PERFEITO!")
        print(f"     ✅ cloud_video_url")
        print(f"     ✅ cloud_thumbnail_url")
        print(f"     ✅ video_transcript ({len(video_transcript)} chars)")
        print(f"     ✅ visual_analysis ({len(visual_analysis)} chars)")
        print(f"     ✅ smart_title")

    print()
    print("-" * 80)
    print()

print()
print("=" * 80)
if all_ok:
    print("🎉 TESTE 100% APROVADO!")
    print("✅ Pode rodar a migração das 50 URLs com segurança.")
else:
    print("⚠️  Alguns problemas detectados.")
print("=" * 80)
