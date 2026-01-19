"""
Debug completo do bookmark Red Bull
"""
import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RED_BULL_ID = 'eefc288c-655a-4abb-b1c7-ac79460d3cf6'

print("=" * 80)
print("🔍 DEBUG COMPLETO - RED BULL x ARCANE")
print("=" * 80)
print()

result = supabase.table('bookmarks').select('*').eq('id', RED_BULL_ID).single().execute()

if not result.data:
    print("❌ Bookmark não encontrado!")
else:
    data = result.data
    
    print(f"📋 BOOKMARK ID: {RED_BULL_ID}")
    print()
    
    # Informações básicas
    print("=" * 80)
    print("INFORMAÇÕES BÁSICAS")
    print("=" * 80)
    print(f"Smart Title: {data.get('smart_title')}")
    print(f"URL do Instagram: {data.get('url')}")
    print(f"Status: {data.get('processing_status')}")
    print(f"Criado em: {data.get('created_at')}")
    print()
    
    # URLs de mídia
    print("=" * 80)
    print("URLs DE MÍDIA")
    print("=" * 80)
    
    cloud_video = data.get('cloud_video_url')
    cloud_thumb = data.get('cloud_thumbnail_url')
    thumbnail = data.get('thumbnail')  # Instagram original
    
    print(f"cloud_video_url:")
    if cloud_video:
        print(f"  ✅ {cloud_video[:100]}...")
    else:
        print(f"  ❌ NULL")
    
    print()
    print(f"cloud_thumbnail_url:")
    if cloud_thumb:
        print(f"  ⚠️  {cloud_thumb}")
        # Testar se existe
        if 'supabase' in cloud_thumb:
            print(f"     (URL do Supabase - vamos testar se arquivo existe)")
        elif 'instagram' in cloud_thumb or 'cdninstagram' in cloud_thumb:
            print(f"     (URL do Instagram - não deveria estar aqui)")
    else:
        print(f"  ❌ NULL")
    
    print()
    print(f"thumbnail (Instagram original):")
    if thumbnail:
        print(f"  {thumbnail[:100]}...")
    else:
        print(f"  ❌ NULL")
    
    print()
    
    # Metadata
    print("=" * 80)
    print("METADATA (extraído pelo Apify)")
    print("=" * 80)
    
    metadata = data.get('metadata')
    if metadata:
        print(f"thumbnail_url no metadata:")
        thumb_in_metadata = metadata.get('thumbnail_url')
        if thumb_in_metadata:
            print(f"  {thumb_in_metadata[:100]}...")
            
            # Verificar se está corrompida
            if 'cdninstagram' in thumb_in_metadata:
                print(f"  ✅ URL válida do Instagram CDN")
            elif 'supabase' in thumb_in_metadata:
                print(f"  ❌ URL corrompida (já é do Supabase?!)")
            else:
                print(f"  ⚠️  URL desconhecida")
        else:
            print(f"  ❌ NULL")
        
        print()
        print(f"Outros campos do metadata:")
        print(f"  - title: {metadata.get('title', 'NULL')[:60]}...")
        print(f"  - platform: {metadata.get('platform', 'NULL')}")
        print(f"  - video_url: {metadata.get('video_url', 'NULL')[:60] if metadata.get('video_url') else 'NULL'}...")
    else:
        print("  ❌ Metadata está NULL")
    
    print()
    
    # Análises
    print("=" * 80)
    print("ANÁLISES DE IA")
    print("=" * 80)
    
    video_transcript = data.get('video_transcript')
    visual_analysis = data.get('visual_analysis')
    
    print(f"video_transcript (Gemini):")
    if video_transcript:
        print(f"  ✅ {len(video_transcript)} caracteres")
        print(f"  Preview: {video_transcript[:100]}...")
    else:
        print(f"  ❌ NULL")
    
    print()
    print(f"visual_analysis (Gemini):")
    if visual_analysis:
        print(f"  ✅ {len(visual_analysis)} caracteres")
    else:
        print(f"  ❌ NULL")
    
    print()
    
    # Diagnóstico
    print("=" * 80)
    print("🔬 DIAGNÓSTICO")
    print("=" * 80)
    print()
    
    issues = []
    
    if not cloud_video:
        issues.append("cloud_video_url está NULL")
    
    if cloud_thumb:
        if 'supabase' in cloud_thumb and len(cloud_thumb) < 120:
            issues.append(f"cloud_thumbnail_url parece truncada ({len(cloud_thumb)} chars)")
        elif 'instagram' in cloud_thumb or 'cdninstagram' in cloud_thumb:
            issues.append("cloud_thumbnail_url aponta para Instagram (deveria ser Supabase)")
    else:
        issues.append("cloud_thumbnail_url está NULL")
    
    if metadata:
        thumb_meta = metadata.get('thumbnail_url')
        if thumb_meta and 'supabase' in thumb_meta:
            issues.append("⚠️  CRÍTICO: metadata.thumbnail_url já vem corrompido do Apify!")
    
    if issues:
        print("❌ PROBLEMAS ENCONTRADOS:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ Nenhum problema encontrado")
    
    print()

print("=" * 80)
