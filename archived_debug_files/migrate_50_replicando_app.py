"""
Script que REPLICA EXATAMENTE o fluxo do app Flutter
Baseado em: lib/services/background_sync_service.dart (linhas 45-162)

FLUXO IDÊNTICO AO APP:
1. Cria bookmark mínimo no Supabase (obter UUID)
2. Chama /api/process-bookmark-complete com timeout de 30s
3. Se sucesso, pega job_id e continua
4. Se timeout, ignora e continua (backend processa mesmo assim)
5. Deixa Render processar em background
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

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def detect_platform(url):
    """Detecta plataforma (igual app Flutter linha 165-174)"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'tiktok.com' in url or 'vm.tiktok.com' in url:
        return 'tiktok'
    return 'other'

def generate_temporary_title(url, platform):
    """Gera título temporário (igual app Flutter linha 176-188)"""
    titles = {
        'youtube': 'YouTube Video (processando...)',
        'instagram': 'Instagram Reel (processando...)',
        'tiktok': 'TikTok Video (processando...)',
    }
    return titles.get(platform, 'Video (processando...)')

def process_bookmark_in_background(url, user_id, user_context=None):
    """
    Replica EXATAMENTE o método processBookmarkInBackground do app Flutter
    (linhas 45-162 de background_sync_service.dart)
    """
    try:
        print(f"🚀 Iniciando processamento em background...")
        print(f"   URL: {url[:60]}...")

        # 1. Criar bookmark mínimo no Supabase (IGUAL APP - linha 60-91)
        print(f"📝 Criando bookmark no Supabase...")

        platform = detect_platform(url)
        now = datetime.utcnow()

        bookmark_data = {
            'url': url,
            'title': generate_temporary_title(url, platform),
            'platform': platform.lower(),
            'user_id': user_id,
            'created_at': now.isoformat(),
            'processing_status': 'queued',  # IGUAL APP (linha 72)
        }

        # Se tem contexto, adicionar (linha 76-78)
        if user_context:
            bookmark_data['user_context_raw'] = user_context

        result = supabase.table('bookmarks').insert(bookmark_data).execute()

        if not result.data:
            raise Exception('Supabase retornou null ao criar bookmark')

        bookmark_id = result.data[0]['id']
        print(f"✅ Bookmark criado: {bookmark_id}")

        # 2. Chamar endpoint backend (IGUAL APP - linha 93-123)
        print(f"📡 Enviando requisição pro backend...")

        backend_url = f'{BACKEND_URL}/api/process-bookmark-complete'

        request_body = {
            'bookmark_id': bookmark_id,
            'url': url,
            'user_id': user_id,
            'extract_metadata': True,   # IGUAL APP (linha 102)
            'analyze_video': True,      # IGUAL APP (linha 103)
            'process_ai': True,         # IGUAL APP (linha 104)
            'upload_to_cloud': True,    # TRUE para migração completa
            'user_context': user_context,  # IGUAL APP (linha 106)
        }

        # POST com timeout de 30s (IGUAL APP - linha 112-123)
        try:
            response = requests.post(
                backend_url,
                json=request_body,
                headers={'Content-Type': 'application/json'},
                timeout=30  # IGUAL APP (linha 119)
            )

            if response.status_code != 200:
                raise Exception(f'Backend retornou status {response.status_code}: {response.text}')

            backend_data = response.json()

            if backend_data.get('success') != True:
                raise Exception(f'Backend falhou: {backend_data.get("error", "erro desconhecido")}')

            job_id = backend_data.get('job_id')
            estimated_time = backend_data.get('estimated_time_seconds', 90)

            print(f"✅ Job enfileirado!")
            print(f"   Job ID: {job_id}")
            print(f"   Tempo estimado: {estimated_time}s")

            return {
                'success': True,
                'bookmark_id': bookmark_id,
                'job_id': job_id,
                'estimated_time': estimated_time
            }

        except requests.exceptions.Timeout:
            # IGUAL APP: se der timeout, ignora e considera sucesso
            # Backend vai processar mesmo assim (linha 120-122)
            print(f"⏱️  Timeout 30s (backend processa mesmo assim)")
            return {
                'success': True,
                'bookmark_id': bookmark_id,
                'job_id': None,
                'timeout': True
            }

    except Exception as e:
        print(f"❌ Erro: {str(e)[:100]}")
        return {
            'success': False,
            'error': str(e)
        }

# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

print("="*80)
print("MIGRAÇÃO - REPLICANDO FLUXO DO APP FLUTTER")
print("="*80)
print()

# Ler CSV
print("📄 Lendo CSV...")
urls_to_migrate = []
csv_rows = []

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_rows.append(row)
        if row['migrado'] == 'NÃO' and len(urls_to_migrate) < 50:
            url = row['URL']
            if ('/reel/' in url or '/share/reel/' in url):
                urls_to_migrate.append({
                    'id': row['ID'],
                    'url': url
                })

print(f"✓ Encontradas {len(urls_to_migrate)} URLs para migrar")
print()

# Processar cada URL (IGUAL APP)
print("📥 Processando bookmarks (igual app Flutter)...")
print()

created_bookmarks = []
failed_bookmarks = []

for idx, item in enumerate(urls_to_migrate, 1):
    url = item['url']
    csv_id = item['id']

    print(f"[{idx}/{len(urls_to_migrate)}] ID {csv_id}")

    # Chamar método que replica EXATAMENTE o app Flutter
    result = process_bookmark_in_background(
        url=url,
        user_id=USER_ID,
        user_context=None  # Sem contexto manual nesta migração
    )

    if result['success']:
        created_bookmarks.append({
            'csv_id': csv_id,
            'url': url,
            'bookmark_id': result['bookmark_id'],
            'job_id': result.get('job_id'),
            'timeout': result.get('timeout', False)
        })
    else:
        failed_bookmarks.append({
            'csv_id': csv_id,
            'url': url,
            'error': result.get('error')
        })

    print()

    # Delay a cada 10 URLs para não sobrecarregar
    if idx % 10 == 0 and idx < len(urls_to_migrate):
        print(f"⏸️  Pausa de 5s ({idx}/{len(urls_to_migrate)} processados)...")
        print()
        time.sleep(5)

# Resultados
print("="*80)
print("✅ MIGRAÇÃO CONCLUÍDA")
print("="*80)
print()

print(f"📊 RESUMO:")
print(f"   Criados: {len(created_bookmarks)}")
print(f"   Falhas: {len(failed_bookmarks)}")
print(f"   Timeouts: {sum(1 for bm in created_bookmarks if bm.get('timeout'))}")
print()

# Salvar IDs
if created_bookmarks:
    with open('migrate_50_bookmark_ids.txt', 'w') as f:
        for bm in created_bookmarks:
            f.write(f"{bm['bookmark_id']}\n")
    print(f"💾 IDs salvos em: migrate_50_bookmark_ids.txt")
    print()

# Atualizar CSV
print("📝 Atualizando CSV...")
migrated_ids = {bm['csv_id'] for bm in created_bookmarks}

with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
    writer.writeheader()

    for row in csv_rows:
        if row['ID'] in migrated_ids:
            row['migrado'] = 'SIM'
            row['data_migracao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow(row)

print(f"✓ CSV atualizado")
print()

if failed_bookmarks:
    print("⚠️  FALHAS:")
    for fail in failed_bookmarks[:5]:
        print(f"   ID {fail['csv_id']}: {fail['error'][:60]}")
    print()

print("✨ Migração finalizada!")
print("   Backend está processando os vídeos em background.")
print("   Acompanhe via Supabase dashboard ou app Flutter.")
