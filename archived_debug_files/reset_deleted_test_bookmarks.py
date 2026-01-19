"""
Reseta no CSV as URLs dos bookmarks de teste que foram deletados
"""
import csv
from datetime import datetime

CSV_FILE = 'instagram_urls_migrated_20251226_214730.csv'

# IDs no CSV que precisam ser resetados
ids_to_reset = [6, 7, 9, 10, 11]

print("=" * 80)
print("RESETANDO URLs NO CSV")
print("=" * 80)
print()

# Ler CSV
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Resetar
resetados = 0
for row in rows:
    if int(row['ID']) in ids_to_reset:
        print(f"Resetando ID {row['ID']}: {row['URL'][:50]}...")
        print(f"  Status anterior: {row['migrado']}")
        row['migrado'] = 'NÃO'
        row['data_migracao'] = ''
        print(f"  Status novo: NÃO")
        print()
        resetados += 1

# Salvar
with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['ID', 'URL', 'migrado', 'data_migracao']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("=" * 80)
print(f"✅ {resetados} URLs resetadas para NÃO")
print("=" * 80)
