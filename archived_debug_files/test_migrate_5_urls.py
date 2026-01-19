"""
Script de TESTE para migrar 5 URLs do Instagram
Verifica se os campos cloud_thumb_url e cloud_video_url estão sendo salvos corretamente
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

# Ler CSV e pegar 5 primeiros não migrados
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

            if len(urls_to_migrate) < 5:  # 🔥 APENAS 5 PARA TESTE
                # Filtrar URLs inválidas (perfis, posts sem reel)
                url = row['URL']
                if ('/reel/' in url or '/share/reel/' in url) and url.count('/') >= 4:
                    urls_to_migrate.append({
                        'id': row['ID'],
                        'url': url
                    })

print(f"✓ Total de linhas no CSV: {total_rows}")
print(f"✓ URLs não migradas: {non_migrated}")
print(f"✓ Selecionadas {len(urls_to_migrate)} URLs para teste")
print()

# Mostrar URLs que serão migradas
print("📋 URLs que serão migradas (TESTE):")
for item in urls_to_migrate:
    print(f"  ID {item['id']}: {item['url']}")
print()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("="*80)
print(f"🧪 TESTE DE MIGRAÇÃO - {len(urls_to_migrate)} VÍDEOS")
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

    print(f"  [{idx}/{len(urls_to_migrate)}] ID {csv_id}: {url}")

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

    # Delay entre requisições
    time.sleep(2)

print()
print("="*80)
print(f"⏳ AGUARDANDO PROCESSAMENTO...")
print("="*80)
print()

if created_bookmarks:
    total_wait_time = sum(bm['estimated_time'] for bm in created_bookmarks)
    print(f"⏱️  Tempo estimado total: {total_wait_time}s (~{total_wait_time//60}min)")
    print(f"⏸️  Aguardando {total_wait_time + 30}s para garantir conclusão...")
    print()

    time.sleep(total_wait_time + 30)  # Aguarda + 30s de margem

print()
print("="*80)
print(f"🔍 VERIFICANDO RESULTADOS NO SUPABASE")
print("="*80)
print()

# PASSO 3: Verificar se os campos foram salvos corretamente
all_ok = True
for bm in created_bookmarks:
    bookmark_id = bm['bookmark_id']
    csv_id = bm['csv_id']

    print(f"📋 Verificando ID CSV {csv_id} (bookmark {bookmark_id})...")

    result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()

    if not result.data:
        print(f"  ❌ Bookmark não encontrado!")
        all_ok = False
        continue

    data = result.data

    # Verificar campos críticos
    processing_status = data.get('processing_status')
    cloud_video_url = data.get('cloud_video_url')
    cloud_thumb_url = data.get('cloud_thumb_url')
    thumbnail_url = data.get('thumbnail_url')
    smart_title = data.get('smart_title')
    gemini_analysis = data.get('gemini_analysis')

    print(f"  Status: {processing_status}")
    print(f"  Smart Title: {smart_title[:60] if smart_title else 'NULL'}...")
    print(f"  Gemini Analysis: {'OK' if gemini_analysis else 'NULL'}")
    print(f"  cloud_video_url: {cloud_video_url[:80] if cloud_video_url else 'NULL'}...")
    print(f"  cloud_thumb_url: {cloud_thumb_url[:80] if cloud_thumb_url else 'NULL'}...")
    print(f"  thumbnail_url (Instagram): {thumbnail_url[:80] if thumbnail_url else 'NULL'}...")

    # Validações
    errors = []

    if processing_status != 'completed':
        errors.append(f"Status esperado 'completed', obtido '{processing_status}'")

    if not cloud_video_url:
        errors.append("cloud_video_url está NULL")
    elif 'supabase' not in cloud_video_url.lower():
        errors.append(f"cloud_video_url não aponta para Supabase: {cloud_video_url}")

    if not cloud_thumb_url:
        errors.append("cloud_thumb_url está NULL")
    elif 'supabase' not in cloud_thumb_url.lower():
        errors.append(f"cloud_thumb_url não aponta para Supabase: {cloud_thumb_url}")
    elif 'instagram.com' in cloud_thumb_url.lower() or 'cdninstagram' in cloud_thumb_url.lower():
        errors.append(f"❌ ERRO CRÍTICO: cloud_thumb_url aponta para Instagram em vez de Supabase: {cloud_thumb_url}")

    if not smart_title:
        errors.append("smart_title está NULL")

    if not gemini_analysis:
        errors.append("gemini_analysis está NULL")

    if errors:
        print(f"  ❌ PROBLEMAS ENCONTRADOS:")
        for error in errors:
            print(f"     - {error}")
        all_ok = False
    else:
        print(f"  ✅ Tudo OK!")

    print()

print()
print("="*80)
print(f"📊 RESUMO DO TESTE")
print("="*80)
print()
print(f"✅ Bookmarks criados: {len(created_bookmarks)}")
print(f"❌ Falhas na criação: {len(failed_bookmarks)}")

if all_ok:
    print()
    print("🎉 TESTE PASSOU! Todos os campos estão corretos.")
    print("✅ Pode rodar a migração completa com segurança.")
else:
    print()
    print("⚠️  TESTE FALHOU! Há problemas nos campos.")
    print("❌ NÃO rode a migração completa até corrigir.")

print()

# Salvar IDs dos bookmarks para inspeção manual
if created_bookmarks:
    with open('test_migrate_5_bookmark_ids.txt', 'w') as f:
        for bm in created_bookmarks:
            f.write(f"{bm['bookmark_id']}\n")
    print(f"💾 IDs salvos em: test_migrate_5_bookmark_ids.txt")
    print()

print("✨ Teste concluído!")
