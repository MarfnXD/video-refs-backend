"""
Verifica quais URLs do CSV já foram processadas no banco de dados
Para evitar duplicatas na migração
"""
import os
import csv
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'
CSV_PATH = 'instagram_urls_migrated_20251226_214730.csv'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🔍 VERIFICANDO URLs DO CSV QUE JÁ FORAM PROCESSADAS")
print("=" * 80)
print()

# Ler CSV
print("📄 Lendo CSV...")
csv_urls = []
csv_rows = []

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_rows.append(row)
        csv_urls.append(row['URL'])

print(f"✓ Total de URLs no CSV: {len(csv_urls)}")
print()

# Buscar todas as URLs do usuário no banco
print("🔎 Buscando URLs processadas no banco...")
result = supabase.table('bookmarks')\
    .select('id, url, processing_status, created_at')\
    .eq('user_id', USER_ID)\
    .execute()

db_bookmarks = result.data or []
print(f"✓ Total de bookmarks no banco: {len(db_bookmarks)}")
print()

# Criar set de URLs do banco para comparação rápida
db_urls = {bm['url'] for bm in db_bookmarks}

# Verificar quais URLs do CSV já estão no banco
already_processed = []
not_processed = []

for row in csv_rows:
    csv_url = row['URL']

    # Normalizar URLs (remover parâmetros extras)
    # Instagram pode ter variações: /reel/XXX, /share/reel/XXX, ?igsh=...
    csv_url_clean = csv_url.split('?')[0].rstrip('/')

    # Verificar se existe no banco (exata ou variação)
    found = False
    matching_bookmark = None

    for db_url in db_urls:
        db_url_clean = db_url.split('?')[0].rstrip('/')
        if csv_url_clean == db_url_clean or csv_url == db_url:
            found = True
            # Buscar o bookmark completo
            matching_bookmark = next((bm for bm in db_bookmarks if bm['url'] == db_url), None)
            break

    if found:
        already_processed.append({
            'csv_id': row['ID'],
            'url': csv_url,
            'bookmark': matching_bookmark
        })
    else:
        not_processed.append({
            'csv_id': row['ID'],
            'url': csv_url
        })

print("=" * 80)
print("📊 RESULTADO DA VERIFICAÇÃO")
print("=" * 80)
print()
print(f"✅ URLs já processadas: {len(already_processed)} ({len(already_processed)*100//len(csv_urls)}%)")
print(f"⏳ URLs não processadas: {len(not_processed)} ({len(not_processed)*100//len(csv_urls)}%)")
print()

if already_processed:
    print("=" * 80)
    print("✅ URLs JÁ PROCESSADAS (primeiras 20):")
    print("=" * 80)
    for item in already_processed[:20]:
        bookmark = item['bookmark']
        status = bookmark.get('processing_status') if bookmark else 'unknown'
        print(f"  ID CSV {item['csv_id']}: {status}")
        print(f"    URL: {item['url'][:70]}...")
        if bookmark:
            print(f"    Bookmark ID: {bookmark['id']}")
            print(f"    Criado em: {bookmark.get('created_at', 'N/A')[:19]}")
        print()

    if len(already_processed) > 20:
        print(f"  ... e mais {len(already_processed) - 20} URLs já processadas")
    print()

if not_processed:
    print("=" * 80)
    print("⏳ URLs NÃO PROCESSADAS (primeiras 20):")
    print("=" * 80)
    for item in not_processed[:20]:
        print(f"  ID CSV {item['csv_id']}: {item['url'][:70]}...")

    if len(not_processed) > 20:
        print(f"  ... e mais {len(not_processed) - 20} URLs não processadas")
    print()

# Verificar inconsistências no CSV
print("=" * 80)
print("🔍 VERIFICANDO INCONSISTÊNCIAS NO CSV")
print("=" * 80)
print()

csv_marked_yes = sum(1 for row in csv_rows if row['migrado'] == 'SIM')
csv_marked_no = sum(1 for row in csv_rows if row['migrado'] == 'NÃO')

print(f"Marcadas como 'SIM' no CSV: {csv_marked_yes}")
print(f"Marcadas como 'NÃO' no CSV: {csv_marked_no}")
print(f"Realmente processadas (banco): {len(already_processed)}")
print()

if csv_marked_yes != len(already_processed):
    diff = abs(csv_marked_yes - len(already_processed))
    print(f"⚠️  INCONSISTÊNCIA: Diferença de {diff} URLs entre CSV e banco!")
    print()

    # Encontrar URLs marcadas como SIM mas não processadas
    marked_yes_but_not_in_db = []
    for row in csv_rows:
        if row['migrado'] == 'SIM':
            csv_url_clean = row['URL'].split('?')[0].rstrip('/')
            found = any(
                csv_url_clean == bm['url'].split('?')[0].rstrip('/')
                for bm in db_bookmarks
            )
            if not found:
                marked_yes_but_not_in_db.append(row)

    if marked_yes_but_not_in_db:
        print(f"❌ URLs marcadas como 'SIM' mas NÃO estão no banco: {len(marked_yes_but_not_in_db)}")
        for row in marked_yes_but_not_in_db[:10]:
            print(f"  ID {row['ID']}: {row['URL'][:60]}...")
        print()
else:
    print("✅ CSV está consistente com o banco de dados!")
    print()

print("=" * 80)
print("💡 RECOMENDAÇÃO")
print("=" * 80)
print()
print(f"Próxima migração deve processar até {min(50, len(not_processed))} URLs das {len(not_processed)} não processadas.")
print()
