"""
Ver todos os campos do bookmark para diagnosticar
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

result = supabase.table('bookmarks').select('*').eq('id', 'd49a39ec-2fc1-4ef0-b8ed-0ce2b5d497e9').execute()

if result.data:
    bm = result.data[0]
    print("="*80)
    print("TODOS OS CAMPOS DO BOOKMARK d49a39ec")
    print("="*80)
    
    # Campos principais
    print(f"✅ title: {bm.get('title', 'N/A')[:60]}")
    print(f"✅ status: {bm.get('processing_status', 'N/A')}")
    print(f"✅ url: {bm.get('url', 'N/A')[:60]}")
    print()
    
    # Upload e storage
    print("UPLOAD/STORAGE:")
    print(f"  cloud_video_url: {'✅' if bm.get('cloud_video_url') else '❌'}")
    print(f"  thumbnail_url: {'✅' if bm.get('thumbnail_url') else '❌'}")
    print()
    
    # Metadados
    print("METADADOS:")
    print(f"  author: {bm.get('author', 'N/A')}")
    print(f"  duration: {bm.get('duration', 'N/A')}")
    print(f"  views: {bm.get('views', 'N/A')}")
    print(f"  likes: {bm.get('likes', 'N/A')}")
    print()
    
    # IA
    print("PROCESSAMENTO IA:")
    print(f"  auto_description: {'✅' if bm.get('auto_description') else '❌'}")
    print(f"  auto_tags: {len(bm.get('auto_tags', [])) if bm.get('auto_tags') else 0} tags")
    print(f"  auto_categories: {len(bm.get('auto_categories', [])) if bm.get('auto_categories') else 0} cats")
    print(f"  smart_title: {'✅' if bm.get('smart_title') else '❌'}")
    print(f"  gemini_analysis_result: {'✅' if bm.get('gemini_analysis_result') else '❌'}")
    print()
    
    # Diagnóstico
    print("="*80)
    print("DIAGNÓSTICO")
    print("="*80)
    
    has_metadata = bool(bm.get('author') or bm.get('duration'))
    has_ai = bool(bm.get('auto_description'))
    has_cloud = bool(bm.get('cloud_video_url'))
    
    print(f"Metadados extraídos: {'✅' if has_metadata else '❌'}")
    print(f"IA processada: {'✅' if has_ai else '❌'}")
    print(f"Upload cloud: {'✅' if has_cloud else '❌'}")
    print()
    
    if has_metadata and has_ai and not has_cloud:
        print("⚠️  PROBLEMA IDENTIFICADO:")
        print("   - Apify extraiu metadados ✅")
        print("   - IA processou conteúdo ✅")
        print("   - Upload para cloud FALHOU ❌")
        print()
        print("   Causa provável: Erro no download/upload do vídeo")
        print("   Solução: Reprocessar com fix de retry")
else:
    print("Bookmark não encontrado")
