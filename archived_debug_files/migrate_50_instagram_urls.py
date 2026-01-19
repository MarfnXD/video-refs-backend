"""
Script para migração COMPLETA dos 50 primeiros vídeos não migrados
- Upload para Supabase Storage
- Análise multimodal via Gemini Flash 2.5
- Processamento IA via Claude 3.5 Sonnet
- Geração de Smart Title via Gemini 3 Pro
"""
import os
import csv
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
CSV_PATH = 'instagram_urls_migrated_20251226_214730.csv'

# Ler CSV e pegar 50 primeiros não migrados
print("📄 Lendo CSV...")
urls_to_migrate = []
csv_rows = []
total_rows = 0
non_migrated = 0

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1
        csv_rows.append(row)

        if row['migrado'] == 'NÃO':
            non_migrated += 1

            if len(urls_to_migrate) < 50:
                # Filtrar URLs inválidas (perfis, posts sem reel)
                url = row['URL']
                if ('/reel/' in url or '/share/reel/' in url) and url.count('/') >= 4:
                    urls_to_migrate.append({
                        'id': row['ID'],
                        'url': url
                    })

print(f"✓ Total de linhas no CSV: {total_rows}")
print(f"✓ URLs não migradas: {non_migrated}")

print(f"✓ Encontradas {len(urls_to_migrate)} URLs válidas para migrar (máx 50)")
print()

# Mostrar algumas URLs que serão migradas
print("📋 Primeiras 10 URLs que serão migradas:")
for item in urls_to_migrate[:10]:
    print(f"  ID {item['id']}: {item['url'][:70]}...")
print()

# Confirmação automática (modo não-interativo)
print("⚠️  Iniciando migração...")
print()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("="*80)
print(f"MIGRAÇÃO COMPLETA - {len(urls_to_migrate)} VÍDEOS")
print("="*80)
print()

# PASSO 1: Deletar bookmarks existentes (se houver)
print("🗑️  PASSO 1: Limpando bookmarks duplicados...")
deleted_count = 0
for item in urls_to_migrate:
    url = item['url']
    result = supabase.table('bookmarks').delete().eq('url', url).eq('user_id', USER_ID).execute()
    if result.data:
        deleted_count += len(result.data)

if deleted_count > 0:
    print(f"  ✓ Removidos {deleted_count} bookmarks duplicados\n")
else:
    print(f"  ✓ Nenhum bookmark duplicado encontrado\n")

# PASSO 2: Criar e enfileirar novos bookmarks
print("📥 PASSO 2: Criando e enfileirando bookmarks...")
print("   🔥 Processamento COMPLETO ativado:")
print("      - Upload para Supabase Storage")
print("      - Análise multimodal Gemini Flash 2.5")
print("      - Processamento IA Claude 3.5 Sonnet")
print("      - Smart Title via Gemini 3 Pro")
print()

created_bookmarks = []
failed_bookmarks = []

for idx, item in enumerate(urls_to_migrate, 1):
    url = item['url']
    csv_id = item['id']

    print(f"  [{idx}/{len(urls_to_migrate)}] ID {csv_id}: {url[:60]}...")

    # Criar bookmark no Supabase
    bookmark_data = {
        'user_id': USER_ID,
        'url': url,
        'platform': 'instagram',
        'processing_status': 'pending',
        'created_at': datetime.utcnow().isoformat()
    }

    try:
        result = supabase.table('bookmarks').insert(bookmark_data).execute()

        if not result.data:
            print(f"    ❌ Erro ao criar bookmark no Supabase")
            failed_bookmarks.append({'csv_id': csv_id, 'url': url, 'error': 'Falha ao criar no Supabase'})
            continue

        bookmark_id = result.data[0]['id']
        print(f"    ✓ Criado: {bookmark_id}")

        # Enfileirar para processamento COM upload_to_cloud=True
        response = requests.post(
            f'{BACKEND_URL}/api/process-bookmark-complete',
            json={
                'bookmark_id': bookmark_id,
                'user_id': USER_ID,
                'url': url,
                'upload_to_cloud': True,  # 🔥 Upload + Gemini + Smart Title
                'user_context': None,
                'manual_tags': [],
                'manual_categories': []
            },
            timeout=30
        )

        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data.get('job_id')
            estimated_time = job_data.get('estimated_time_seconds', 0)
            print(f"    ✅ Enfileirado: job_id={job_id}")
            print(f"    ⏱️  Tempo estimado: {estimated_time}s")

            created_bookmarks.append({
                'csv_id': csv_id,
                'url': url,
                'bookmark_id': bookmark_id,
                'job_id': job_id,
                'estimated_time': estimated_time
            })
        else:
            print(f"    ❌ Erro ao enfileirar: {response.status_code}")
            print(f"    {response.text[:100]}")
            failed_bookmarks.append({'csv_id': csv_id, 'url': url, 'error': f'HTTP {response.status_code}'})

    except Exception as e:
        print(f"    ❌ Erro: {str(e)[:100]}")
        failed_bookmarks.append({'csv_id': csv_id, 'url': url, 'error': str(e)[:100]})

    # Pequeno delay para não sobrecarregar
    if idx % 10 == 0:
        print(f"\n  ⏸️  Pausa de 5s (processados {idx}/{len(urls_to_migrate)})...\n")
        time.sleep(5)

print()
print("="*80)
print(f"✅ MIGRAÇÃO INICIADA")
print("="*80)
print()

# Salvar IDs dos bookmarks criados
if created_bookmarks:
    print("💾 Salvando IDs dos bookmarks para monitoramento...")
    with open('migrate_50_bookmark_ids.txt', 'w') as f:
        for bm in created_bookmarks:
            f.write(f"{bm['bookmark_id']}\n")
    print(f"✓ IDs salvos em: migrate_50_bookmark_ids.txt")
    print()

# Atualizar CSV
print("📝 Atualizando CSV com status de migração...")
migrated_ids = {bm['csv_id'] for bm in created_bookmarks}

with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
    writer.writeheader()

    for row in csv_rows:
        if row['ID'] in migrated_ids:
            row['migrado'] = 'SIM'
            row['data_migracao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow(row)

print(f"✓ CSV atualizado: {CSV_PATH}")
print()

# Mostrar resumo
print("📊 RESUMO FINAL:")
print(f"   ✅ Bookmarks criados: {len(created_bookmarks)}")
print(f"   ❌ Falhas: {len(failed_bookmarks)}")
print(f"   ⏱️  Tempo total estimado: {sum(bm['estimated_time'] for bm in created_bookmarks)//60} minutos")
print()

if failed_bookmarks:
    print("⚠️  URLs QUE FALHARAM:")
    for fail in failed_bookmarks[:10]:
        print(f"   ID {fail['csv_id']}: {fail['error']}")
    if len(failed_bookmarks) > 10:
        print(f"   ... e mais {len(failed_bookmarks) - 10} falhas")
    print()

print("🎯 PROCESSAMENTO ATIVADO:")
print("   ✓ Upload para Supabase Storage")
print("   ✓ Análise multimodal Gemini Flash 2.5")
print("   ✓ Processamento IA Claude 3.5 Sonnet")
print("   ✓ Smart Title via Gemini 3 Pro")
print()

print("⏰ Processamento em andamento no servidor Render...")
print("   Vídeos serão processados em background via Celery workers")
print()

# Salvar log de migração
log_file = f'migrate_50_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
with open(log_file, 'w') as f:
    f.write(f"MIGRAÇÃO DE 50 VÍDEOS - {datetime.now()}\n")
    f.write("="*80 + "\n\n")
    f.write(f"Total enfileirado: {len(created_bookmarks)}\n")
    f.write(f"Total falhas: {len(failed_bookmarks)}\n\n")

    if created_bookmarks:
        f.write("BOOKMARKS CRIADOS:\n")
        for bm in created_bookmarks:
            f.write(f"  ID CSV {bm['csv_id']}: {bm['bookmark_id']}\n")

    if failed_bookmarks:
        f.write("\nFALHAS:\n")
        for fail in failed_bookmarks:
            f.write(f"  ID CSV {fail['csv_id']}: {fail['error']}\n")

print(f"📄 Log salvo em: {log_file}")
print()
print("✨ Migração concluída! Acompanhe o progresso via Supabase dashboard.")
