#!/usr/bin/env python3
"""
Script de teste para verificar fluxo Gemini → Claude
Cria um bookmark de teste e processa via API
"""
import os
import requests
import time
from supabase import create_client

# Config
BACKEND_URL = "https://video-refs-backend.onrender.com"
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Video de teste (Instagram - Monsters Inc que estava dando problema)
TEST_URL = "https://www.instagram.com/reel/DR-NF7DjdvN/"
USER_ID = "0ed9bb40-0041-4dca-9649-256cb418f403"  # Marco

def main():
    print("🧪 TESTE DE FLUXO GEMINI → CLAUDE")
    print("=" * 80)

    # 1. Criar bookmark de teste
    print("\n1️⃣ Criando bookmark de teste...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    bookmark_data = {
        'user_id': USER_ID,
        'url': TEST_URL,
        'title': 'TEST - Gemini Flow Debug',
        'platform': 'instagram',
        'processing_status': 'queued',
    }

    result = supabase.table('bookmarks').insert(bookmark_data).execute()
    bookmark_id = result.data[0]['id']
    print(f"✅ Bookmark criado: {bookmark_id}")

    # 2. Chamar endpoint de processamento
    print("\n2️⃣ Chamando endpoint de processamento...")
    response = requests.post(
        f"{BACKEND_URL}/api/process-bookmark-complete",
        json={
            "bookmark_id": bookmark_id,
            "user_id": USER_ID,
            "url": TEST_URL,
            "upload_to_cloud": True,
            "process_ai": True
        }
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # 3. Aguardar processamento (60-90s)
    print("\n3️⃣ Aguardando processamento...")
    print("⏳ Isso pode demorar 60-90 segundos (Apify + Upload + Gemini + Claude)...")

    for i in range(18):  # 90 segundos = 18 * 5s
        time.sleep(5)

        # Check status
        bookmark = supabase.table('bookmarks').select('processing_status').eq('id', bookmark_id).execute()
        status = bookmark.data[0]['processing_status']

        print(f"   [{(i+1)*5}s] Status: {status}")

        if status == 'completed':
            print("\n✅ Processamento COMPLETO!")
            break
        elif status == 'failed':
            print("\n❌ Processamento FALHOU!")
            break

    # 4. Verificar resultado
    print("\n4️⃣ Verificando resultado no banco...")
    bookmark = supabase.table('bookmarks').select(
        'id, processing_status, video_transcript, visual_analysis, auto_description, auto_tags, auto_categories, error_message'
    ).eq('id', bookmark_id).execute()

    b = bookmark.data[0]
    print(f"\n📊 RESULTADO:")
    print(f"   Status: {b.get('processing_status')}")
    print(f"   Gemini transcript: {len(b.get('video_transcript', '') or '')} chars")
    print(f"   Gemini visual: {len(b.get('visual_analysis', '') or '')} chars")
    print(f"   Claude description: {b.get('auto_description', 'N/A')}")
    print(f"   Claude tags: {b.get('auto_tags', [])}")
    print(f"   Claude categories: {b.get('auto_categories', [])}")
    if b.get('error_message'):
        print(f"   ❌ Error: {b.get('error_message')}")

    # 5. Mostrar preview da análise Gemini
    if b.get('visual_analysis'):
        print(f"\n📝 PREVIEW ANÁLISE GEMINI (primeiros 500 chars):")
        print(b.get('visual_analysis')[:500])
        print("...")

    print("\n" + "=" * 80)
    print("✅ Teste completo!")
    print(f"🔍 Verifique os logs do Render para ver os DEBUG logs:")
    print(f"   https://dashboard.render.com/web/srv-cpgd7iu8ii6s73a0pq6g/logs")

if __name__ == "__main__":
    main()
