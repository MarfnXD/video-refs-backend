"""
Script para:
1. Deletar todos bookmarks existentes
2. Cadastrar os 5 primeiros vídeos da lista
3. Atualizar CSV com coluna de migração
"""
import os
import csv
import requests
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

# Config
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')  # Corrigido
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

CSV_INPUT = 'instagram_urls_simplified_20251226_103701.csv'
CSV_OUTPUT = f'instagram_urls_migrated_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

print("🚀 MIGRAÇÃO DOS 5 PRIMEIROS VÍDEOS")
print("=" * 60)

# Conectar Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# PASSO 1: Deletar TODOS os bookmarks do usuário
# ============================================================
print("\n🗑️ PASSO 1: Deletando todos os bookmarks...")

try:
    result = supabase.table('bookmarks').delete().eq('user_id', USER_ID).execute()
    deletados = len(result.data) if result.data else 0
    print(f"✅ {deletados} bookmarks deletados")
except Exception as e:
    print(f"⚠️ Erro ao deletar (pode estar vazio): {str(e)}")

# ============================================================
# PASSO 2: Ler CSV e pegar os 5 primeiros
# ============================================================
print("\n📖 PASSO 2: Lendo CSV...")

videos = []
with open(CSV_INPUT, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        videos.append({
            'id': row['ID'],
            'url': row['URL']
        })

primeiros_5 = videos[:5]
print(f"✅ {len(primeiros_5)} vídeos para processar:")
for v in primeiros_5:
    print(f"   {v['id']}. {v['url'][:50]}...")

# ============================================================
# PASSO 3: Cadastrar os 5 primeiros
# ============================================================
print("\n⚙️ PASSO 3: Cadastrando e enfileirando processamento...")

bookmark_ids = []

for video in primeiros_5:
    try:
        # 3.1: Criar bookmark no Supabase
        result = supabase.table('bookmarks').insert({
            'url': video['url'],
            'user_id': USER_ID,
            'processing_status': 'pending'
        }).execute()

        bookmark_id = result.data[0]['id']
        bookmark_ids.append(bookmark_id)

        print(f"\n✅ Vídeo {video['id']} criado: {bookmark_id[:8]}...")

        # 3.2: Enfileirar processamento completo
        response = requests.post(f'{BACKEND_URL}/api/process-bookmark-complete', json={
            'bookmark_id': bookmark_id,
            'user_id': USER_ID,
            'url': video['url']
        })

        if response.status_code == 200:
            job_data = response.json()
            print(f"   ⏳ Job enfileirado: {job_data.get('job_id', 'N/A')[:8]}...")
        else:
            print(f"   ❌ Erro ao enfileirar: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")

# ============================================================
# PASSO 4: Atualizar CSV com coluna "migrado"
# ============================================================
print(f"\n📝 PASSO 4: Criando novo CSV com coluna 'migrado'...")

migrados_ids = [v['id'] for v in primeiros_5]

with open(CSV_INPUT, 'r') as f_in, open(CSV_OUTPUT, 'w', newline='') as f_out:
    reader = csv.DictReader(f_in)
    fieldnames = reader.fieldnames + ['migrado', 'data_migracao']

    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        if row['ID'] in migrados_ids:
            row['migrado'] = 'SIM'
            row['data_migracao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            row['migrado'] = 'NÃO'
            row['data_migracao'] = ''

        writer.writerow(row)

print(f"✅ CSV atualizado salvo em: {CSV_OUTPUT}")

# ============================================================
# RESUMO
# ============================================================
print("\n" + "=" * 60)
print("📊 RESUMO:")
print(f"   🗑️ Bookmarks deletados: todos do usuário")
print(f"   ✅ Bookmarks criados: {len(bookmark_ids)}")
print(f"   ⏳ Jobs enfileirados: {len(bookmark_ids)}")
print(f"   📝 CSV atualizado: {CSV_OUTPUT}")
print("\n🎉 Migração completa!")
print("\n💡 Próximos passos:")
print(f"   1. Aguardar ~5-10min para processamento dos {len(bookmark_ids)} vídeos")
print(f"   2. Verificar status no Supabase ou rodar script de monitoramento")
print("=" * 60)
