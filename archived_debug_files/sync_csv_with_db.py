"""
Sincroniza o CSV com o banco de dados
Marca como 'SIM' as URLs que já foram processadas
"""
import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'
CSV_PATH = 'instagram_urls_migrated_20251226_214730.csv'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🔄 SINCRONIZANDO CSV COM BANCO DE DADOS")
print("=" * 80)
print()

# Buscar todas as URLs processadas
print("🔎 Buscando URLs processadas no banco...")
result = supabase.table('bookmarks')\
    .select('url, created_at')\
    .eq('user_id', USER_ID)\
    .execute()

db_bookmarks = result.data or []
db_urls_set = {bm['url'].split('?')[0].rstrip('/'): bm for bm in db_bookmarks}

print(f"✓ {len(db_bookmarks)} bookmarks encontrados")
print()

# Ler e atualizar CSV
print("📄 Lendo CSV...")
csv_rows = []
updates = 0

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_url_clean = row['URL'].split('?')[0].rstrip('/')

        # Verificar se está no banco
        if csv_url_clean in db_urls_set and row['migrado'] != 'SIM':
            # Precisa atualizar
            bookmark = db_urls_set[csv_url_clean]
            row['migrado'] = 'SIM'
            row['data_migracao'] = bookmark['created_at'][:19].replace('T', ' ')
            updates += 1
            print(f"  ✅ Marcando ID {row['ID']} como processada")

        csv_rows.append(row)

print()
print(f"✓ {updates} linhas precisam de atualização")
print()

if updates > 0:
    # Salvar CSV atualizado
    print("💾 Salvando CSV atualizado...")
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'URL', 'migrado', 'data_migracao'])
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"✅ CSV atualizado: {CSV_PATH}")
    print()

    # Estatísticas finais
    total_sim = sum(1 for row in csv_rows if row['migrado'] == 'SIM')
    total_nao = sum(1 for row in csv_rows if row['migrado'] == 'NÃO')

    print("=" * 80)
    print("📊 ESTATÍSTICAS ATUALIZADAS")
    print("=" * 80)
    print(f"Marcadas como 'SIM': {total_sim}")
    print(f"Marcadas como 'NÃO': {total_nao}")
    print(f"Total: {len(csv_rows)}")
    print()
else:
    print("✅ CSV já está sincronizado com o banco!")
    print()
