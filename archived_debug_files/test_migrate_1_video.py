"""
Script de TESTE: Migrar 1 vídeo com relatório de qualidade completo
- Upload para Supabase Storage
- Análise multimodal via Gemini Flash 2.5
- Processamento IA via Claude 3.5 Sonnet
- Smart Title via Gemini 3 Pro
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import time

load_dotenv()

# Config
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

# URL de teste (primeira não migrada do CSV)
TEST_URL = 'https://www.instagram.com/reel/DDhW5iLRaTP/'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("="*80)
print("TESTE DE MIGRAÇÃO - 1 VÍDEO COM RELATÓRIO COMPLETO")
print("="*80)
print(f"\n📹 URL: {TEST_URL}\n")

# PASSO 1: Deletar bookmark existente (se houver)
print("🗑️  PASSO 1: Limpando bookmark duplicado (se existir)...")
result = supabase.table('bookmarks').delete().eq('url', TEST_URL).eq('user_id', USER_ID).execute()
if result.data:
    print(f"  ✓ Removido bookmark duplicado (ID: {result.data[0]['id']})\n")
else:
    print(f"  ✓ Nenhum bookmark duplicado encontrado\n")

# PASSO 2: Criar bookmark
print("📥 PASSO 2: Criando bookmark no Supabase...")
bookmark_data = {
    'user_id': USER_ID,
    'url': TEST_URL,
    'platform': 'instagram',
    'processing_status': 'pending',
    'created_at': datetime.utcnow().isoformat()
}

result = supabase.table('bookmarks').insert(bookmark_data).execute()
if not result.data:
    print("❌ ERRO ao criar bookmark")
    exit(1)

bookmark_id = result.data[0]['id']
print(f"  ✅ Bookmark criado: {bookmark_id}\n")

# PASSO 3: Enfileirar para processamento COMPLETO
print("🚀 PASSO 3: Enfileirando para processamento COMPLETO...")
print("   🔥 Processamento ativado:")
print("      - Upload para Supabase Storage")
print("      - Análise multimodal Gemini Flash 2.5")
print("      - Processamento IA Claude 3.5 Sonnet")
print("      - Smart Title via Gemini 3 Pro\n")

try:
    response = requests.post(
        f'{BACKEND_URL}/api/process-bookmark-complete',
        json={
            'bookmark_id': bookmark_id,
            'user_id': USER_ID,
            'url': TEST_URL,
            'upload_to_cloud': True,  # 🔥 Processamento completo
            'user_context': None,
            'manual_tags': [],
            'manual_categories': []
        },
        timeout=120
    )

    if response.status_code != 200:
        print(f"❌ ERRO ao enfileirar: {response.status_code}")
        print(f"   {response.text}")
        exit(1)

    job_data = response.json()
    job_id = job_data.get('job_id')
    estimated_time = job_data.get('estimated_time_seconds', 0)

    print(f"  ✅ Enfileirado com sucesso!")
    print(f"     Job ID: {job_id}")
    print(f"     Tempo estimado: {estimated_time}s\n")

except Exception as e:
    print(f"❌ ERRO: {str(e)}")
    exit(1)

# PASSO 4: Monitorar processamento
print("⏰ PASSO 4: Monitorando processamento...\n")
print("   Aguardando conclusão (timeout: 5 minutos)...")

max_wait_time = 300  # 5 minutos
check_interval = 10  # Check a cada 10s
elapsed_time = 0
last_status = None

while elapsed_time < max_wait_time:
    time.sleep(check_interval)
    elapsed_time += check_interval

    # Buscar status atual
    result = supabase.table('bookmarks').select('processing_status, title, smart_title').eq('id', bookmark_id).execute()

    if not result.data:
        print("   ⚠️  Bookmark não encontrado")
        break

    current_status = result.data[0]['processing_status']

    # Mostrar mudança de status
    if current_status != last_status:
        print(f"   [{elapsed_time}s] Status: {current_status}")
        last_status = current_status

    # Verificar se concluído
    if current_status == 'completed':
        print(f"\n   ✅ Processamento concluído em {elapsed_time}s!\n")
        break
    elif current_status == 'failed':
        print(f"\n   ❌ Processamento falhou!\n")
        break

if elapsed_time >= max_wait_time:
    print(f"\n   ⏱️  Timeout atingido ({max_wait_time}s). Verifique manualmente.\n")

# PASSO 5: Gerar relatório de qualidade
print("="*80)
print("📊 RELATÓRIO DE QUALIDADE")
print("="*80)
print()

result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).execute()

if not result.data:
    print("❌ Erro ao buscar dados do bookmark")
    exit(1)

bm = result.data[0]

# Informações básicas
print(f"🎬 INFORMAÇÕES BÁSICAS")
print(f"   ID: {bookmark_id}")
print(f"   URL: {TEST_URL}")
print(f"   Status: {bm['processing_status']}")
print(f"   Criado em: {bm['created_at']}")
print()

# ETAPA 1: Metadados
print(f"📊 ETAPA 1: EXTRAÇÃO DE METADADOS (Apify)")
if bm.get('title'):
    print(f"   ✅ Título: {bm['title']}")
    print(f"   ✅ Plataforma: {bm['platform']}")
    if bm.get('author'):
        print(f"   ✅ Autor: {bm['author']}")
    if bm.get('views'):
        print(f"   ✅ Views: {bm['views']:,}")
    if bm.get('likes'):
        print(f"   ✅ Likes: {bm['likes']:,}")
    if bm.get('duration'):
        print(f"   ✅ Duração: {bm['duration']}s")
    if bm.get('published_at'):
        print(f"   ✅ Publicado em: {bm['published_at']}")
else:
    print(f"   ❌ Metadados não extraídos")
print()

# ETAPA 2: Análise Gemini
print(f"🎬 ETAPA 2: ANÁLISE VISUAL E ÁUDIO (Gemini 2.5 Flash)")
if bm.get('gemini_analysis_result'):
    analysis = bm['gemini_analysis_result']

    if isinstance(analysis, dict):
        if analysis.get('transcription'):
            transcription = analysis['transcription']
            print(f"   ✅ Transcrição: {len(transcription)} caracteres")
            print(f"      Preview: {transcription[:150]}...")

        if analysis.get('visual_analysis'):
            visual = analysis['visual_analysis']
            print(f"   ✅ Análise Visual: {len(visual)} caracteres")
            print(f"      Preview: {visual[:150]}...")

        if analysis.get('is_fooh') is not None:
            print(f"   ✅ FOOH: {'Sim' if analysis['is_fooh'] else 'Não'}")
    else:
        print(f"   ✅ Análise completa: {len(str(analysis))} caracteres")
else:
    print(f"   ❌ Análise Gemini não realizada")
print()

# ETAPA 3: Processamento IA (Claude)
print(f"🤖 ETAPA 3: PROCESSAMENTO FINAL (Claude 3.5 Sonnet)")
if bm.get('auto_description'):
    print(f"   ✅ Descrição Automática:")
    print(f"      {bm['auto_description']}")
else:
    print(f"   ❌ Descrição não gerada")

if bm.get('auto_tags'):
    tags = bm['auto_tags']
    print(f"   ✅ Tags: {len(tags)} tags")
    print(f"      {', '.join(tags[:10])}")
else:
    print(f"   ❌ Tags não geradas")

if bm.get('auto_categories'):
    cats = bm['auto_categories']
    print(f"   ✅ Categorias: {len(cats)} categorias")
    print(f"      {', '.join(cats)}")
else:
    print(f"   ❌ Categorias não geradas")

if bm.get('relevance_score') is not None:
    print(f"   ✅ Score de Relevância: {bm['relevance_score']:.2f}/1.00")
else:
    print(f"   ❌ Score não calculado")
print()

# ETAPA 4: Smart Title (Gemini 3 Pro)
print(f"✨ ETAPA 4: SMART TITLE (Gemini 3.0 Pro)")
if bm.get('smart_title'):
    print(f"   ✅ Smart Title: {bm['smart_title']}")
    print(f"      Tamanho: {len(bm['smart_title'])} caracteres")
else:
    print(f"   ❌ Smart Title não gerado")
print()

# Cloud Storage
print(f"☁️  CLOUD STORAGE")
if bm.get('cloud_video_url'):
    print(f"   ✅ Vídeo no cloud: {bm['cloud_video_url'][:80]}...")
else:
    print(f"   ❌ Vídeo não enviado para cloud")

if bm.get('thumbnail_url'):
    print(f"   ✅ Thumbnail: {bm['thumbnail_url'][:80]}...")
else:
    print(f"   ❌ Thumbnail não gerada")
print()

# Resumo final
print("="*80)
print("📋 RESUMO FINAL")
print("="*80)
print(f"   Metadados extraídos: {'✅' if bm.get('title') else '❌'}")
print(f"   Análise Gemini: {'✅' if bm.get('gemini_analysis_result') else '❌'}")
print(f"   Processamento IA: {'✅' if bm.get('auto_description') else '❌'}")
print(f"   Smart Title: {'✅' if bm.get('smart_title') else '❌'}")
print(f"   Upload cloud: {'✅' if bm.get('cloud_video_url') else '❌'}")
print(f"   Status final: {bm['processing_status']}")
print()

# Salvar relatório detalhado
report_file = f'test_migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(f"# 📊 RELATÓRIO DE TESTE - MIGRAÇÃO DE 1 VÍDEO\n")
    f.write(f"**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    f.write(f"**Bookmark ID**: {bookmark_id}\n")
    f.write(f"**URL**: {TEST_URL}\n")
    f.write(f"---\n\n")

    f.write(f"## 🎬 INFORMAÇÕES BÁSICAS\n")
    f.write(f"- **Status**: `{bm['processing_status']}`\n")
    f.write(f"- **Criado em**: {bm['created_at']}\n\n")

    f.write(f"## 📊 ETAPA 1: METADADOS (Apify)\n")
    if bm.get('title'):
        f.write(f"- **Título**: {bm['title']}\n")
        f.write(f"- **Plataforma**: {bm['platform']}\n")
        if bm.get('author'):
            f.write(f"- **Autor**: {bm['author']}\n")
        if bm.get('description'):
            f.write(f"- **Descrição**: {bm['description'][:200]}...\n")
        if bm.get('views'):
            f.write(f"- **Views**: {bm['views']:,}\n")
        if bm.get('likes'):
            f.write(f"- **Likes**: {bm['likes']:,}\n")
        if bm.get('duration'):
            f.write(f"- **Duração**: {bm['duration']}s\n")
    else:
        f.write("❌ Metadados não extraídos\n")
    f.write("\n")

    f.write(f"## 🎬 ETAPA 2: ANÁLISE GEMINI (Flash 2.5)\n")
    if bm.get('gemini_analysis_result'):
        analysis = bm['gemini_analysis_result']
        if isinstance(analysis, dict):
            if analysis.get('transcription'):
                f.write(f"**Transcrição** ({len(analysis['transcription'])} caracteres):\n")
                f.write(f"```\n{analysis['transcription'][:500]}...\n```\n\n")
            if analysis.get('visual_analysis'):
                f.write(f"**Análise Visual**:\n{analysis['visual_analysis'][:500]}...\n\n")
            if analysis.get('is_fooh') is not None:
                f.write(f"**FOOH**: {'Sim' if analysis['is_fooh'] else 'Não'}\n\n")
    else:
        f.write("❌ Análise não realizada\n\n")

    f.write(f"## 🤖 ETAPA 3: PROCESSAMENTO IA (Claude 3.5 Sonnet)\n")
    if bm.get('auto_description'):
        f.write(f"**Descrição Automática**:\n{bm['auto_description']}\n\n")
    if bm.get('auto_tags'):
        f.write(f"**Tags** ({len(bm['auto_tags'])} tags):\n")
        f.write(f"`{'`, `'.join(bm['auto_tags'])}`\n\n")
    if bm.get('auto_categories'):
        f.write(f"**Categorias**: {', '.join(bm['auto_categories'])}\n\n")
    if bm.get('relevance_score') is not None:
        f.write(f"**Score**: {bm['relevance_score']:.2f}/1.00\n\n")

    f.write(f"## ✨ ETAPA 4: SMART TITLE (Gemini 3.0 Pro)\n")
    if bm.get('smart_title'):
        f.write(f"**Smart Title**: {bm['smart_title']}\n\n")
    else:
        f.write("❌ Smart Title não gerado\n\n")

    f.write(f"## ☁️  CLOUD STORAGE\n")
    if bm.get('cloud_video_url'):
        f.write(f"- **Vídeo**: {bm['cloud_video_url']}\n")
    if bm.get('thumbnail_url'):
        f.write(f"- **Thumbnail**: {bm['thumbnail_url']}\n")
    f.write("\n")

    f.write(f"## 📋 RESUMO\n")
    f.write(f"- Metadados: {'✅' if bm.get('title') else '❌'}\n")
    f.write(f"- Análise Gemini: {'✅' if bm.get('gemini_analysis_result') else '❌'}\n")
    f.write(f"- Processamento IA: {'✅' if bm.get('auto_description') else '❌'}\n")
    f.write(f"- Smart Title: {'✅' if bm.get('smart_title') else '❌'}\n")
    f.write(f"- Cloud: {'✅' if bm.get('cloud_video_url') else '❌'}\n")
    f.write(f"- Status: `{bm['processing_status']}`\n")

print(f"📄 Relatório salvo em: {report_file}")
print()

if bm['processing_status'] == 'completed':
    print("✅ TESTE BEM-SUCEDIDO! Pipeline completo funcionando.")
    print("   Pronto para migrar os 50 vídeos.")
else:
    print("⚠️  TESTE INCOMPLETO. Verifique os erros acima antes de prosseguir.")
