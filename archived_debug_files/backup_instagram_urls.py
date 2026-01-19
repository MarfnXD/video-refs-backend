#!/usr/bin/env python3
"""
Script de backup de URLs de vídeos do Instagram
Extrai apenas dados essenciais para reimportar depois
"""

import os
import json
import csv
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")  # Nome correto no .env

def backup_instagram_urls():
    """Faz backup de todas as URLs do Instagram"""

    print("🔌 Conectando ao Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    print("📥 Buscando bookmarks do Instagram...")
    response = supabase.table('bookmarks') \
        .select('id, user_id, url, user_context_raw, user_context_processed, tags, categories, projects, title, created_at') \
        .eq('platform', 'instagram') \
        .order('created_at', desc=False) \
        .execute()

    bookmarks = response.data
    total = len(bookmarks)

    print(f"✅ Encontrados {total} bookmarks do Instagram")

    if total == 0:
        print("❌ Nenhum bookmark do Instagram encontrado!")
        return

    # Prepara dados para exportação
    export_data = []
    for b in bookmarks:
        export_data.append({
            'id': b.get('id'),
            'user_id': b.get('user_id'),
            'url': b.get('url'),
            'title': b.get('title', ''),
            'user_context_raw': b.get('user_context_raw', ''),
            'user_context_processed': b.get('user_context_processed', ''),
            'tags': b.get('tags', []),
            'categories': b.get('categories', []),
            'projects': b.get('projects', []),
            'created_at': b.get('created_at'),
        })

    # Timestamp para nome dos arquivos
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Exporta para JSON (mais fácil de reimportar)
    json_filename = f'backup_instagram_urls_{timestamp}.json'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON salvo: {json_filename}")

    # Exporta para CSV (mais fácil de visualizar)
    csv_filename = f'backup_instagram_urls_{timestamp}.csv'
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'user_id', 'url', 'title', 'user_context_raw', 'user_context_processed',
            'tags', 'categories', 'projects', 'created_at'
        ])
        writer.writeheader()

        for row in export_data:
            # Converte listas para string separada por vírgula
            row_copy = row.copy()
            row_copy['tags'] = ', '.join(row['tags']) if row['tags'] else ''
            row_copy['categories'] = ', '.join(row['categories']) if row['categories'] else ''
            row_copy['projects'] = ', '.join(row['projects']) if row['projects'] else ''
            writer.writerow(row_copy)

    print(f"📊 CSV salvo: {csv_filename}")

    # Estatísticas
    users = set(b['user_id'] for b in export_data)
    with_context = sum(1 for b in export_data if b['user_context_raw'] or b['user_context_processed'])
    with_tags = sum(1 for b in export_data if b['tags'])

    print("\n📈 ESTATÍSTICAS:")
    print(f"   Total de bookmarks: {total}")
    print(f"   Usuários únicos: {len(users)}")
    print(f"   Com contexto manual: {with_context}")
    print(f"   Com tags manuais: {with_tags}")
    print("\n✅ Backup concluído com sucesso!")

if __name__ == "__main__":
    backup_instagram_urls()
