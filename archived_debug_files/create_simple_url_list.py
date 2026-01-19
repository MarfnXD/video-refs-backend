#!/usr/bin/env python3
"""
Cria lista simplificada: apenas ID provisório + URL do vídeo
"""

import csv
from datetime import datetime

# Lê o backup CSV original
input_file = 'backup_instagram_urls_20251226_102443.csv'
output_file = f'instagram_urls_simplified_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

print(f"📥 Lendo arquivo: {input_file}")

urls = []
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        urls.append(row['url'])

print(f"✅ Total de URLs encontradas: {len(urls)}")

# Cria arquivo simplificado
print(f"💾 Criando arquivo simplificado: {output_file}")

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['ID', 'URL'])
    
    for idx, url in enumerate(urls, start=1):
        writer.writerow([idx, url])

print(f"✅ Arquivo criado com sucesso!")
print(f"\n📊 RESUMO:")
print(f"   Total de vídeos: {len(urls)}")
print(f"   Arquivo: {output_file}")
print(f"   Formato: ID (1, 2, 3...) + URL")
