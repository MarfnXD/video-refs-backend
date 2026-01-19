#!/usr/bin/env python3
"""
Script simples para processar 3 vídeos de teste.
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

# 3 vídeos para teste
VIDEOS = [
    "https://www.instagram.com/reel/DPHYVUwD7D0/?igsh=ancyZGlwbXZsNWx1",
    "https://www.instagram.com/reel/DCXInoBSICF/",
    "https://www.instagram.com/reel/DBv5oCVxtog/"
]

print("🧪 PROCESSAMENTO DE 3 VÍDEOS TESTE\n")
print(f"📍 Backend: {BACKEND_URL}")
print(f"👤 User ID: {USER_ID}\n")

for idx, url in enumerate(VIDEOS, 1):
    print(f"\n{'='*70}")
    print(f"📹 Vídeo {idx}/3")
    print(f"{'='*70}")
    print(f"URL: {url[:60]}...")

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

    # 3. Enfileirar processamento
    print("  ⚙️  Enfileirando processamento...")

    payload = {
        "bookmark_id": bookmark_id,
        "url": url,
        "user_id": USER_ID,
        "extract_metadata": True,
        "analyze_video": True,  # ✅ GEMINI 2.5 FLASH - Análise visual COMPLETA
        "process_ai": True,
        "upload_to_cloud": True,  # ✅ UPLOAD - Necessário para Gemini analisar vídeo
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
print("✅ 3 vídeos enfileirados para processamento")
print("⏳ Aguarde ~3-5 minutos para processamento completar")
print("\n📍 Como monitorar:")
print("1. Render Dashboard: https://dashboard.render.com")
print("2. Services → video-refs-backend-worker → Logs")
print("3. Buscar por: [PIPELINE] ou [METADATA] ou [GEMINI]")
print()
