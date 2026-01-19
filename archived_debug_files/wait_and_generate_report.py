"""
Script para aguardar processamento completar e gerar relatório automático
"""
import os
import time
from dotenv import load_dotenv
from supabase import create_client
import json
from datetime import datetime

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
user_id = '0ed9bb40-0041-4dca-9649-256cb418f403'

# Ler IDs dos bookmarks
try:
    with open('bookmarks_processing_ids.txt', 'r') as f:
        bookmark_ids = [line.strip() for line in f.readlines()]
except FileNotFoundError:
    print("❌ Arquivo bookmarks_processing_ids.txt não encontrado")
    exit(1)

print("="*80)
print("⏰ AGUARDANDO PROCESSAMENTO COMPLETAR...")
print("="*80)
print()

# Aguardar até todos completarem
max_checks = 40  # 40 x 30s = 20 minutos
for i in range(max_checks):
    # Buscar status de todos
    statuses = []
    for bookmark_id in bookmark_ids:
        res = supabase.table('bookmarks').select('processing_status, error_message').eq('id', bookmark_id).execute()
        if res.data:
            status = res.data[0]['processing_status']
            error = res.data[0].get('error_message', '')
            statuses.append((status, error))
        else:
            statuses.append(('not_found', ''))

    # Contar por status
    completed = sum(1 for s, _ in statuses if s == 'completed')
    failed = sum(1 for s, _ in statuses if s == 'failed')
    processing = sum(1 for s, _ in statuses if s in ['queued', 'processing'])

    print(f"[{i+1}/{max_checks}] ✅ {completed}/5 | ⚙️  {processing}/5 | ❌ {failed}/5")

    # Se todos completaram ou falharam, parar
    if completed + failed == 5:
        print()
        print("="*80)
        print("🎉 PROCESSAMENTO FINALIZADO!")
        print("="*80)
        print(f"   ✅ Completos: {completed}")
        print(f"   ❌ Falhados: {failed}")
        print()
        break

    time.sleep(30)
else:
    print()
    print("⚠️  Timeout: Aguardou 20 minutos. Gerando relatório parcial...")
    print()

# GERAR RELATÓRIO
print("📝 Gerando relatório detalhado...")
print()

# Buscar todos os campos dos 5 bookmarks
result = supabase.table('bookmarks').select('*').in_('id', bookmark_ids).execute()

if not result.data:
    print("❌ Nenhum bookmark encontrado")
    exit(1)

# Ordenar por created_at
bookmarks = sorted(result.data, key=lambda x: x['created_at'], reverse=True)

# Gerar relatório
report_lines = []
report_lines.append("="*80)
report_lines.append("RELATÓRIO COMPLETO - SMART TITLES COM CLOUD + GEMINI ANALYSIS")
report_lines.append("="*80)
report_lines.append("")

for i, bm in enumerate(bookmarks, 1):
    report_lines.append("="*80)
    report_lines.append(f"VÍDEO {i}: {bm['url'][:60]}...")
    report_lines.append("="*80)
    report_lines.append("")

    # FASE 1: CRIAÇÃO
    report_lines.append("🔵 FASE 1: CRIAÇÃO NO SUPABASE")
    report_lines.append(f"   Bookmark ID: {bm['id']}")
    report_lines.append(f"   Criado em: {bm.get('created_at', 'N/A')}")
    report_lines.append(f"   Status inicial: pending")
    report_lines.append("")

    # FASE 2: EXTRAÇÃO DE METADADOS (APIFY)
    metadata = bm.get('metadata', {})
    if isinstance(metadata, str):
        metadata = json.loads(metadata) if metadata else {}

    report_lines.append("🟢 FASE 2: EXTRAÇÃO DE METADADOS (APIFY)")
    if metadata:
        report_lines.append(f"   ✅ STATUS: Sucesso")
        report_lines.append(f"   Título: {metadata.get('title', 'N/A')[:80]}...")
        report_lines.append(f"   Descrição: {len(metadata.get('description', ''))} caracteres")

        views = metadata.get("views", "N/A")
        report_lines.append(f"   Views: {views:,}" if isinstance(views, (int, float)) else f"   Views: {views}")

        likes = metadata.get("likes", "N/A")
        report_lines.append(f"   Likes: {likes:,}" if isinstance(likes, (int, float)) else f"   Likes: {likes}")

        comments = metadata.get("comments_count", "N/A")
        report_lines.append(f"   Comments: {comments:,}" if isinstance(comments, (int, float)) else f"   Comments: {comments}")

        hashtags = metadata.get('hashtags', [])
        report_lines.append(f"   Hashtags: {len(hashtags)}")
        if hashtags:
            report_lines.append(f"      Exemplos: {hashtags[:3]}")

        top_comments = metadata.get('top_comments', [])
        report_lines.append(f"   Top Comments capturados: {len(top_comments)}")
        if top_comments:
            comment1 = top_comments[0]
            text1 = comment1.get("text", "") if isinstance(comment1, dict) else str(comment1)
            report_lines.append(f"      Exemplo 1: \"{text1[:60]}...\"")
            if len(top_comments) > 1:
                comment2 = top_comments[1]
                text2 = comment2.get("text", "") if isinstance(comment2, dict) else str(comment2)
                report_lines.append(f"      Exemplo 2: \"{text2[:60]}...\"")
    else:
        report_lines.append(f"   ❌ STATUS: Sem metadados")
    report_lines.append("")

    # FASE 3: ANÁLISE DE VÍDEO (GEMINI 2.5 FLASH)
    report_lines.append("🟣 FASE 3: ANÁLISE DE VÍDEO (GEMINI 2.5 FLASH)")
    video_transcript = bm.get('video_transcript', '')
    visual_analysis = bm.get('visual_analysis', '')

    if video_transcript or visual_analysis:
        report_lines.append(f"   ✅ STATUS: Executado")
        report_lines.append(f"   Transcrição: {len(video_transcript)} caracteres")
        if video_transcript:
            report_lines.append(f"      Preview: \"{video_transcript[:100]}...\"")
        report_lines.append(f"   Análise Visual: {len(visual_analysis)} caracteres")
        if visual_analysis and visual_analysis != video_transcript:
            report_lines.append(f"      Preview: \"{visual_analysis[:100]}...\"")
    else:
        report_lines.append(f"   ❌ STATUS: NÃO EXECUTADO")
        cloud_url = bm.get('cloud_video_url', '')
        if not cloud_url:
            report_lines.append(f"   Motivo: Upload para cloud falhou ou não foi concluído")
        else:
            report_lines.append(f"   Motivo: Erro ao analisar vídeo com Gemini")
    report_lines.append("")

    # FASE 4: PROCESSAMENTO IA (GEMINI 3 PRO)
    report_lines.append("🟠 FASE 4: PROCESSAMENTO IA (GEMINI 3 PRO via Claude Service)")
    auto_tags = bm.get('auto_tags', [])
    auto_categories = bm.get('auto_categories', [])
    auto_description = bm.get('auto_description', '')
    smart_title = bm.get('smart_title', '')

    if auto_tags or auto_categories or auto_description:
        report_lines.append(f"   ✅ STATUS: Sucesso")
        report_lines.append(f"   Auto Tags: {len(auto_tags)}")
        if auto_tags:
            report_lines.append(f"      {auto_tags}")
        report_lines.append(f"   Auto Categorias: {len(auto_categories)}")
        if auto_categories:
            report_lines.append(f"      {auto_categories}")
        report_lines.append(f"   Auto Descrição: {len(auto_description)} caracteres")
        if auto_description:
            report_lines.append(f"      \"{auto_description[:150]}...\"")
        report_lines.append(f"   Smart Title: {len(smart_title)} caracteres")
        if smart_title:
            report_lines.append(f"      \"{smart_title}\"")
        else:
            report_lines.append(f"      ⚠️  Smart Title NÃO foi gerado!")
    else:
        report_lines.append(f"   ❌ STATUS: Falhou ou não executou")
    report_lines.append("")

    # FASE 5: SALVAMENTO
    report_lines.append("🔴 FASE 5: SALVAMENTO NO SUPABASE")
    report_lines.append(f"   Status final: {bm.get('processing_status', 'N/A')}")
    report_lines.append(f"   Processamento iniciado: {bm.get('processing_started_at', 'N/A')}")
    report_lines.append(f"   Processamento completado: {bm.get('processing_completed_at', 'N/A')}")
    report_lines.append(f"   Erro: {bm.get('error_message') if bm.get('error_message') else 'Nenhum'}")

    # Cloud sync
    cloud_url = bm.get('cloud_video_url', '')
    if cloud_url:
        report_lines.append(f"   ☁️  Cloud Video URL: {cloud_url[:80]}...")

    # Calcular tempo total
    if bm.get('processing_started_at') and bm.get('processing_completed_at'):
        start = datetime.fromisoformat(bm['processing_started_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(bm['processing_completed_at'].replace('Z', '+00:00'))
        duration = (end - start).total_seconds()
        report_lines.append(f"   Tempo total: {duration:.1f} segundos")

    report_lines.append("")
    report_lines.append("")

# Salvar relatório
report_content = "\n".join(report_lines)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"COMPLETE_TEST_REPORT_{timestamp}.md"

with open(filename, 'w') as f:
    f.write(report_content)

print(f"✅ Relatório gerado: {filename}")
print()

# Também salvar versão em TXT
txt_filename = filename.replace('.md', '.txt')
with open(txt_filename, 'w') as f:
    f.write(report_content)

print(f"✅ Cópia em TXT: {txt_filename}")
print()
print("="*80)
print("✓ PROCESSO COMPLETO!")
print("="*80)
