#!/usr/bin/env python3
"""
Verifica a análise do Gemini no último bookmark processado
"""
import os
from supabase import create_client

supabase_url = "https://twwpcnyqpwznzarguzit.supabase.co"
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Buscar último bookmark processado (pelo timestamp)
response = supabase.table('bookmarks').select(
    'id, title, video_transcript, visual_analysis, transcript_language, '
    'analyzed_at, cloud_video_url, auto_tags, auto_categories, metadata'
).order('created_at', desc=True).limit(1).execute()

if response.data:
    bookmark = response.data[0]

    print("\n" + "="*80)
    print("🎬 ANÁLISE GEMINI - ÚLTIMO VÍDEO PROCESSADO")
    print("="*80)

    print(f"\n📌 BOOKMARK: {bookmark['id'][:8]}...")
    print(f"📝 Título: {bookmark.get('title', 'N/A')}")
    print(f"⏰ Analisado em: {bookmark.get('analyzed_at', 'N/A')}")
    print(f"🌐 Idioma: {bookmark.get('transcript_language', 'N/A')}")

    print("\n" + "-"*80)
    print("🎤 TRANSCRIÇÃO (video_transcript):")
    print("-"*80)
    transcript = bookmark.get('video_transcript')
    if transcript:
        print(f"📊 Tamanho: {len(transcript)} caracteres")
        print(f"\n{transcript}")
    else:
        print("❌ Nenhuma transcrição encontrada")

    print("\n" + "-"*80)
    print("👁️ ANÁLISE VISUAL (visual_analysis):")
    print("-"*80)
    visual = bookmark.get('visual_analysis')
    if visual:
        print(f"📊 Tamanho: {len(visual)} caracteres")
        print(f"\n{visual}")
    else:
        print("❌ Nenhuma análise visual encontrada")

    print("\n" + "-"*80)
    print("🤖 RESULTADO CLAUDE (usando input do Gemini):")
    print("-"*80)
    print(f"🏷️ Tags: {bookmark.get('auto_tags', [])}")
    print(f"📁 Categorias: {bookmark.get('auto_categories', [])}")

    print("\n" + "-"*80)
    print("☁️ CLOUD:")
    print("-"*80)
    cloud_url = bookmark.get('cloud_video_url')
    if cloud_url:
        print(f"✅ Vídeo na cloud: {cloud_url[:80]}...")
    else:
        print("❌ Vídeo não está na cloud")

    # Metadata do Apify
    metadata = bookmark.get('metadata')
    if metadata:
        print("\n" + "-"*80)
        print("📥 METADADOS APIFY:")
        print("-"*80)
        print(f"   Views: {metadata.get('views', 'N/A')}")
        print(f"   Likes: {metadata.get('likes', 'N/A')}")
        print(f"   Comentários: {metadata.get('comments_count', 'N/A')}")
        print(f"   Duração: {metadata.get('duration', 'N/A')}")

    print("\n" + "="*80 + "\n")
else:
    print("❌ Nenhum bookmark encontrado")
