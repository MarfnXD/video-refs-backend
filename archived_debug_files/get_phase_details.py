"""
Script para extrair detalhes fase a fase dos vídeos processados
"""
import os
from dotenv import load_dotenv
from supabase import create_client
import json
from datetime import datetime

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
user_id = '0ed9bb40-0041-4dca-9649-256cb418f403'

# Buscar todos os campos dos 5 bookmarks
result = supabase.table('bookmarks').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(5).execute()

for i, bm in enumerate(result.data, 1):
    print('=' * 80)
    print(f'VÍDEO {i}: {bm["url"][:60]}...')
    print('=' * 80)
    print()

    # FASE 1: CRIAÇÃO
    print('🔵 FASE 1: CRIAÇÃO NO SUPABASE')
    print(f'   Bookmark ID: {bm["id"]}')
    print(f'   Criado em: {bm.get("created_at", "N/A")}')
    print(f'   Status inicial: pending')
    print()

    # FASE 2: EXTRAÇÃO DE METADADOS (APIFY)
    metadata = bm.get('metadata', {})
    if isinstance(metadata, str):
        metadata = json.loads(metadata) if metadata else {}

    print('🟢 FASE 2: EXTRAÇÃO DE METADADOS (APIFY)')
    if metadata:
        print(f'   ✅ STATUS: Sucesso')
        print(f'   Título: {metadata.get("title", "N/A")[:80]}...')
        print(f'   Descrição: {len(metadata.get("description", ""))} caracteres')

        views = metadata.get("views", "N/A")
        print(f'   Views: {views:,}' if isinstance(views, (int, float)) else f'   Views: {views}')

        likes = metadata.get("likes", "N/A")
        print(f'   Likes: {likes:,}' if isinstance(likes, (int, float)) else f'   Likes: {likes}')

        comments = metadata.get("comments_count", "N/A")
        print(f'   Comments: {comments:,}' if isinstance(comments, (int, float)) else f'   Comments: {comments}')

        # Hashtags
        hashtags = metadata.get('hashtags', [])
        print(f'   Hashtags: {len(hashtags)}')
        if hashtags and len(hashtags) > 0:
            print(f'      Exemplos: {hashtags[:3]}')

        # Top Comments
        top_comments = metadata.get('top_comments', [])
        print(f'   Top Comments capturados: {len(top_comments)}')
        if top_comments and len(top_comments) > 0:
            comment1 = top_comments[0]
            text1 = comment1.get("text", "") if isinstance(comment1, dict) else str(comment1)
            print(f'      Exemplo 1: "{text1[:60]}..."')
            if len(top_comments) > 1:
                comment2 = top_comments[1]
                text2 = comment2.get("text", "") if isinstance(comment2, dict) else str(comment2)
                print(f'      Exemplo 2: "{text2[:60]}..."')
    else:
        print(f'   ❌ STATUS: Sem metadados')
    print()

    # FASE 3: ANÁLISE DE VÍDEO (GEMINI 2.5 FLASH)
    print('🟣 FASE 3: ANÁLISE DE VÍDEO (GEMINI 2.5 FLASH)')
    video_transcript = bm.get('video_transcript', '')
    visual_analysis = bm.get('visual_analysis', '')

    if video_transcript or visual_analysis:
        print(f'   ✅ STATUS: Executado')
        print(f'   Transcrição: {len(video_transcript)} caracteres')
        if video_transcript:
            print(f'      Preview: "{video_transcript[:100]}..."')
        print(f'   Análise Visual: {len(visual_analysis)} caracteres')
        if visual_analysis and visual_analysis != video_transcript:
            print(f'      Preview: "{visual_analysis[:100]}..."')
    else:
        print(f'   ❌ STATUS: NÃO EXECUTADO (upload_to_cloud=False)')
        print(f'   Motivo: Análise de vídeo só roda quando upload_to_cloud=True')
    print()

    # FASE 4: PROCESSAMENTO IA (GEMINI 3 PRO)
    print('🟠 FASE 4: PROCESSAMENTO IA (GEMINI 3 PRO via Claude Service)')
    auto_tags = bm.get('auto_tags', [])
    auto_categories = bm.get('auto_categories', [])
    auto_description = bm.get('auto_description', '')
    smart_title = bm.get('smart_title', '')

    if auto_tags or auto_categories or auto_description:
        print(f'   ✅ STATUS: Sucesso')
        print(f'   Auto Tags: {len(auto_tags)}')
        if auto_tags:
            print(f'      {auto_tags}')
        print(f'   Auto Categorias: {len(auto_categories)}')
        if auto_categories:
            print(f'      {auto_categories}')
        print(f'   Auto Descrição: {len(auto_description)} caracteres')
        if auto_description:
            print(f'      "{auto_description[:150]}..."')
        print(f'   Smart Title: {len(smart_title)} caracteres')
        if smart_title:
            print(f'      "{smart_title}"')
    else:
        print(f'   ❌ STATUS: Falhou ou não executou')
    print()

    # FASE 5: SALVAMENTO
    print('🔴 FASE 5: SALVAMENTO NO SUPABASE')
    print(f'   Status final: {bm.get("processing_status", "N/A")}')
    print(f'   Processamento iniciado: {bm.get("processing_started_at", "N/A")}')
    print(f'   Processamento completado: {bm.get("processing_completed_at", "N/A")}')
    print(f'   Erro: {bm.get("error_message", "Nenhum")}')

    # Calcular tempo total
    if bm.get('processing_started_at') and bm.get('processing_completed_at'):
        start = datetime.fromisoformat(bm['processing_started_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(bm['processing_completed_at'].replace('Z', '+00:00'))
        duration = (end - start).total_seconds()
        print(f'   Tempo total: {duration:.1f} segundos')

    print()
    print()
