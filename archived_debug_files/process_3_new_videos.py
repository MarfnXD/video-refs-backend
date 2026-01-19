#!/usr/bin/env python3
"""
Script para processar 3 NOVOS vídeos de teste após correções do Gemini.
Testa se as correções funcionam:
1. max_output_tokens: 16384 (análise completa de vídeos)
2. Sem duplicação de timeline no relatório
"""
import os
import uuid
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Config
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
BACKEND_URL = "https://video-refs-backend.onrender.com"
USER_ID = "0ed9bb40-0041-4dca-9649-256cb418f403"

# 3 vídeos NOVOS para teste (não processados antes)
VIDEOS = [
    "https://www.instagram.com/reel/DDhW5iLRaTP/",
    "https://www.instagram.com/reel/DDh7L7Ah2jg/",
    "https://www.instagram.com/reel/DDzlHZgSby8/"
]

print("🧪 TESTE DAS CORREÇÕES - 3 VÍDEOS NOVOS\n")
print(f"📍 Backend: {BACKEND_URL}")
print(f"👤 User ID: {USER_ID}\n")

for idx, url in enumerate(VIDEOS, 1):
    print(f"\n{'='*70}")
    print(f"📹 Vídeo {idx}/3")
    print(f"{'='*70}")
    print(f"URL: {url}")

    # 1. Deletar bookmark se já existe
    print("  🗑️  Deletando bookmark antigo (se existir)...")
    supabase.table('bookmarks').delete().eq('url', url).eq('user_id', USER_ID).execute()
    print("  ✓ Limpo")

    # 2. Criar bookmark
    print("  📝 Criando bookmark...")
    bookmark_id = str(uuid.uuid4())

    bookmark_data = {
        'id': bookmark_id,
        'user_id': USER_ID,
        'url': url,
        'processing_status': 'pending',
    }

    result = supabase.table('bookmarks').insert(bookmark_data).execute()

    if not result.data:
        print("  ❌ ERRO ao criar bookmark!")
        continue

    print(f"  ✓ Bookmark criado: {bookmark_id[:8]}...")

    # 3. Enfileirar processamento COMPLETO
    print("  ⚙️  Enfileirando processamento COMPLETO...")

    payload = {
        "bookmark_id": bookmark_id,
        "url": url,
        "user_id": USER_ID,
        "extract_metadata": True,
        "analyze_video": True,  # ✅ GEMINI 2.5 FLASH (max_output_tokens: 16384)
        "process_ai": True,
        "upload_to_cloud": True,  # ✅ UPLOAD - Necessário para Gemini
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/process-bookmark-complete",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id', 'N/A')
            print(f"  ✅ Enfileirado: job {job_id[:8]}...")
        else:
            print(f"  ❌ Erro {response.status_code}: {response.text[:100]}")

    except Exception as e:
        print(f"  ❌ Exceção: {e}")

print(f"\n{'='*70}")
print("📊 RESUMO")
print(f"{'='*70}")
print("✅ 3 vídeos NOVOS enfileirados para processamento")
print("⏳ Aguarde ~3-5 minutos para processamento completar")
print("\n🔬 OBJETIVO DO TESTE:")
print("1. Gemini analisa vídeos COMPLETOS (não para em 15s)")
print("2. Relatório NÃO mostra timeline duplicada")
print("\n📍 Como monitorar:")
print("1. Render Dashboard: https://dashboard.render.com")
print("2. Services → video-refs-backend-worker → Logs")
print("3. Buscar por: [PIPELINE] ou [GEMINI]")
print()
