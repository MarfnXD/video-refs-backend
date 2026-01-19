"""
Script para migração COMPLETA dos 5 vídeos COM upload para cloud e análise Gemini
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

# URLs dos 5 vídeos (mesmos do teste anterior)
VIDEOS = [
    'https://www.instagram.com/reel/DCT3tH_ASuC/',
    'https://www.instagram.com/reel/DCotA2wNOd1/',
    'https://www.instagram.com/reel/DBv5oCVxtog/',
    'https://www.instagram.com/reel/DCXInoBSICF/',
    'https://www.instagram.com/reel/DPHYVUwD7D0/?igsh=ancyZGlwbXZsNWx1',
]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("="*80)
print("MIGRAÇÃO COMPLETA - 5 VÍDEOS COM CLOUD + GEMINI ANALYSIS")
print("="*80)
print()

# PASSO 1: Deletar bookmarks existentes
print("🗑️  PASSO 1: Deletando bookmarks existentes...")
deleted_count = 0
for url in VIDEOS:
    result = supabase.table('bookmarks').delete().eq('url', url).eq('user_id', USER_ID).execute()
    if result.data:
        deleted_count += len(result.data)
        print(f"  ✅ Deletado: {url[:60]}...")
    else:
        print(f"  ⚠️  Não encontrado: {url[:60]}...")

print(f"\n✓ Total deletado: {deleted_count} bookmarks\n")

# PASSO 2: Criar e enfileirar novos bookmarks
print("📥 PASSO 2: Criando e enfileirando novos bookmarks...")
print("   ⚠️  ATENÇÃO: upload_to_cloud=TRUE (processamento completo)\n")

created_bookmarks = []

for idx, url in enumerate(VIDEOS, 1):
    print(f"  [{idx}/5] Processando: {url[:60]}...")

    # Criar bookmark no Supabase
    bookmark_data = {
        'user_id': USER_ID,
        'url': url,
        'platform': 'instagram',
        'processing_status': 'pending',
        'created_at': datetime.utcnow().isoformat()
    }

    result = supabase.table('bookmarks').insert(bookmark_data).execute()

    if not result.data:
        print(f"    ❌ Erro ao criar bookmark no Supabase")
        continue

    bookmark_id = result.data[0]['id']
    print(f"    ✓ Criado: {bookmark_id}")

    # Enfileirar para processamento COM upload_to_cloud=True
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/process-bookmark-complete',
            json={
                'bookmark_id': bookmark_id,
                'user_id': USER_ID,
                'url': url,
                'upload_to_cloud': True,  # 🔥 ATIVADO para teste completo
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
                'url': url,
                'bookmark_id': bookmark_id,
                'job_id': job_id,
                'estimated_time': estimated_time
            })
        else:
            print(f"    ❌ Erro ao enfileirar: {response.status_code}")
            print(f"    {response.text}")

    except Exception as e:
        print(f"    ❌ Erro: {str(e)}")

    print()

print("="*80)
print(f"✅ MIGRAÇÃO INICIADA: {len(created_bookmarks)}/5 vídeos enfileirados")
print("="*80)
print()

# Salvar IDs para monitoramento
print("💾 Salvando IDs dos bookmarks para monitoramento...")
with open('bookmarks_processing_ids.txt', 'w') as f:
    for bm in created_bookmarks:
        f.write(f"{bm['bookmark_id']}\n")

print(f"✓ IDs salvos em: bookmarks_processing_ids.txt")
print()

# Mostrar resumo
print("📊 RESUMO:")
print(f"   Bookmarks criados: {len(created_bookmarks)}")
print(f"   Tempo total estimado: {sum(bm['estimated_time'] for bm in created_bookmarks)}s")
print(f"   Upload para cloud: ✅ ATIVADO (Fase 3 Gemini será executada)")
print()

print("⏰ Processamento em andamento no servidor...")
print("   Use o script de monitoramento para acompanhar o progresso.")
