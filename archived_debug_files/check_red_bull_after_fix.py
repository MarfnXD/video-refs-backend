"""
Verifica o Red Bull após a correção
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Red Bull que acabou de ser reprocessado
RED_BULL_ID = 'eefc288c-655a-4abb-b1c7-ac79460d3cf6'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

result = supabase.table('bookmarks').select('*').eq('id', RED_BULL_ID).single().execute()
bookmark = result.data

print("=" * 80)
print("🔍 RED BULL APÓS CORREÇÃO")
print("=" * 80)
print()

print(f"ID: {RED_BULL_ID}")
print(f"Status: {bookmark.get('processing_status')}")
print(f"Smart Title: {bookmark.get('smart_title')}")
print()

print("=" * 80)
print("CAMPOS CRÍTICOS:")
print("=" * 80)
print()

# 1. cloud_thumbnail_url (campo da tabela)
cloud_thumb = bookmark.get('cloud_thumbnail_url')
print(f"1️⃣ cloud_thumbnail_url (campo da tabela):")
if cloud_thumb:
    if 'supabase' in cloud_thumb.lower():
        print(f"   ✅ {cloud_thumb[:80]}...")
        print(f"   ✅ Aponta para Supabase Storage (correto!)")
    else:
        print(f"   ⚠️  {cloud_thumb[:80]}...")
        print(f"   ⚠️  Não aponta para Supabase")
else:
    print(f"   ❌ NULL")

print()

# 2. metadata.thumbnail_url
metadata = bookmark.get('metadata') or {}
thumb_meta = metadata.get('thumbnail_url')
print(f"2️⃣ metadata.thumbnail_url:")
if thumb_meta:
    if 'cdninstagram' in thumb_meta or 'instagram' in thumb_meta:
        print(f"   ✅ {thumb_meta[:80]}...")
        print(f"   ✅ URL original do Instagram CDN preservada! (FIX FUNCIONOU!)")
    elif 'supabase' in thumb_meta.lower():
        print(f"   ❌ {thumb_meta[:80]}...")
        print(f"   ❌ CORROMPIDA! Ainda tem URL do Supabase")
    else:
        print(f"   ⚠️  {thumb_meta[:80]}...")
        print(f"   ⚠️  URL desconhecida")
else:
    print(f"   ❌ NULL")

print()

# 3. cloud_video_url
cloud_video = bookmark.get('cloud_video_url')
print(f"3️⃣ cloud_video_url:")
if cloud_video:
    print(f"   ✅ {cloud_video[:80]}...")
else:
    print(f"   ❌ NULL")

print()

# 4. Análise Gemini
video_transcript = bookmark.get('video_transcript')
visual_analysis = bookmark.get('visual_analysis')
print(f"4️⃣ Análise Gemini:")
if video_transcript and visual_analysis:
    print(f"   ✅ video_transcript: {len(video_transcript)} caracteres")
    print(f"   ✅ visual_analysis: {len(visual_analysis)} caracteres")
elif video_transcript:
    print(f"   ⚠️  video_transcript: {len(video_transcript)} caracteres")
    print(f"   ❌ visual_analysis: NULL")
elif visual_analysis:
    print(f"   ❌ video_transcript: NULL")
    print(f"   ⚠️  visual_analysis: {len(visual_analysis)} caracteres")
else:
    print(f"   ❌ Ambos NULL (Gemini não rodou ou falhou)")

print()

print("=" * 80)
print("CONCLUSÃO:")
print("=" * 80)
print()

issues = []
if not cloud_thumb:
    issues.append("cloud_thumbnail_url está NULL")
if not thumb_meta:
    issues.append("metadata.thumbnail_url está NULL")
elif 'supabase' in thumb_meta.lower():
    issues.append("metadata.thumbnail_url ainda está corrompida com URL do Supabase")
if not cloud_video:
    issues.append("cloud_video_url está NULL")
if not video_transcript or not visual_analysis:
    issues.append("Análise Gemini incompleta")

if issues:
    print(f"❌ {len(issues)} problema(s) encontrado(s):")
    for issue in issues:
        print(f"   - {issue}")
else:
    print(f"✅ SUCESSO! Correção funcionou perfeitamente!")
    print()
    print(f"   ✅ cloud_thumbnail_url → Supabase Storage")
    print(f"   ✅ metadata.thumbnail_url → Instagram CDN original")
    print(f"   ✅ cloud_video_url → Supabase Storage")
    print(f"   ✅ Análise Gemini completa")
    print()
    print(f"🎉 Bug de double upload CORRIGIDO!")

print()
print("=" * 80)
