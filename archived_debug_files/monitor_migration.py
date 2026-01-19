"""
Script para monitorar o status dos vídeos migrados
"""
import os
import time
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

# Config
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

# Conectar ao Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("📊 MONITORAMENTO DE MIGRAÇÃO")
print("=" * 80)
print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Buscar todos os bookmarks do usuário
result = supabase.table('bookmarks').select(
    'id, url, processing_status, smart_title, error_message, auto_tags, auto_categories'
).eq('user_id', USER_ID).order('created_at', desc=True).execute()

bookmarks = result.data

if not bookmarks:
    print("❌ Nenhum bookmark encontrado")
    exit(0)

print(f"📝 Total de bookmarks: {len(bookmarks)}")
print()

# Contadores
status_counts = {
    'pending': 0,
    'queued': 0,
    'processing': 0,
    'completed': 0,
    'failed': 0
}

# Detalhes por bookmark
for i, bm in enumerate(bookmarks, 1):
    status = bm['processing_status']
    status_counts[status] = status_counts.get(status, 0) + 1

    status_emoji = {
        'pending': '⏸️',
        'queued': '⏳',
        'processing': '⚙️',
        'completed': '✅',
        'failed': '❌'
    }.get(status, '❓')

    print(f"{i}. {status_emoji} {status.upper()}")
    print(f"   URL: {bm['url'][:60]}...")
    print(f"   ID: {bm['id'][:8]}...")

    if status == 'completed':
        smart_title = bm.get('smart_title')
        auto_tags = bm.get('auto_tags', [])
        auto_categories = bm.get('auto_categories', [])

        if smart_title:
            print(f"   ✅ Smart Title: {smart_title}")
        else:
            print(f"   ⚠️ Smart Title: NÃO GERADO")

        if auto_tags:
            print(f"   🏷️ Tags: {', '.join(auto_tags[:5])}{' ...' if len(auto_tags) > 5 else ''}")

        if auto_categories:
            print(f"   📁 Categorias: {', '.join(auto_categories)}")

    elif status == 'failed':
        error = bm.get('error_message', 'Sem detalhes')
        print(f"   ❌ Erro: {error[:100]}")

    print()

# Resumo
print("=" * 80)
print("📊 RESUMO:")
for status, count in status_counts.items():
    if count > 0:
        emoji = {
            'pending': '⏸️',
            'queued': '⏳',
            'processing': '⚙️',
            'completed': '✅',
            'failed': '❌'
        }.get(status, '❓')
        print(f"   {emoji} {status.capitalize()}: {count}")

print()

# Progresso
total = len(bookmarks)
completed = status_counts['completed']
failed = status_counts['failed']
in_progress = total - completed - failed

if in_progress > 0:
    print(f"⏳ Processamento em andamento: {in_progress}/{total} vídeos")
    print(f"   Aguarde alguns minutos e rode o script novamente")
elif failed > 0:
    print(f"⚠️ {failed}/{total} vídeos falharam - verifique os erros acima")
else:
    print(f"🎉 TODOS OS {total} VÍDEOS PROCESSADOS COM SUCESSO!")

    # Verificar se todos têm smart_title
    missing_smart_title = [bm for bm in bookmarks if bm['processing_status'] == 'completed' and not bm.get('smart_title')]

    if missing_smart_title:
        print(f"⚠️ ATENÇÃO: {len(missing_smart_title)} vídeos sem smart_title!")
        for bm in missing_smart_title:
            print(f"   - {bm['url'][:60]}...")
    else:
        print(f"✅ Todos os vídeos têm smart_title gerado!")

print("=" * 80)
