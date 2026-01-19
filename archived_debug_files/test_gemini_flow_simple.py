#!/usr/bin/env python3
"""
Script de teste simplificado para verificar fluxo Gemini → Claude
"""
import os
import requests
import time
import json

# Config
BACKEND_URL = "https://video-refs-backend.onrender.com"
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Video de teste (Instagram - Monsters Inc que estava dando problema)
TEST_URL = "https://www.instagram.com/reel/DR-NF7DjdvN/"
USER_ID = "0ed9bb40-0041-4dca-9649-256cb418f403"  # Marco

def supabase_request(method, table, body=None, select=None, eq_column=None, eq_value=None):
    """Helper para requisições Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    params = {}
    if select:
        params['select'] = select
    if eq_column and eq_value:
        params[eq_column] = f"eq.{eq_value}"

    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }

    if method == 'POST':
        response = requests.post(url, headers=headers, json=body, params=params)
    elif method == 'GET':
        response = requests.get(url, headers=headers, params=params)

    return response.json()

def main():
    print("🧪 TESTE DE FLUXO GEMINI → CLAUDE")
    print("=" * 80)

    # 1. Criar bookmark de teste
    print("\n1️⃣ Criando bookmark de teste...")

    bookmark_data = {
        'user_id': USER_ID,
        'url': TEST_URL,
        'title': 'TEST - Gemini Flow Debug',
        'platform': 'instagram',
        'processing_status': 'queued',
    }

    result = supabase_request('POST', 'bookmarks', body=bookmark_data)
    bookmark_id = result[0]['id']
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
    print("   (Veja logs do Render: https://dashboard.render.com/web/srv-cpgd7iu8ii6s73a0pq6g/logs)")

    for i in range(18):  # 90 segundos = 18 * 5s
        time.sleep(5)

        # Check status
        bookmark = supabase_request('GET', 'bookmarks',
                                   select='processing_status',
                                   eq_column='id',
                                   eq_value=bookmark_id)
        status = bookmark[0]['processing_status']

        print(f"   [{(i+1)*5}s] Status: {status}")

        if status == 'completed':
            print("\n✅ Processamento COMPLETO!")
            break
        elif status == 'failed':
            print("\n❌ Processamento FALHOU!")
            break

    # 4. Verificar resultado
    print("\n4️⃣ Verificando resultado no banco...")
    bookmark = supabase_request('GET', 'bookmarks',
                               select='id, processing_status, video_transcript, visual_analysis, auto_description, auto_tags, auto_categories, error_message',
                               eq_column='id',
                               eq_value=bookmark_id)

    b = bookmark[0]
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
    print(f"\n🔍 PRÓXIMO PASSO: Verifique os logs DEBUG no Render:")
    print(f"   https://dashboard.render.com/web/srv-cpgd7iu8ii6s73a0pq6g/logs")
    print(f"\n   Procure por:")
    print(f"   - '📊 Gemini analysis recebido'")
    print(f"   - '📝 Timeline extraído'")
    print(f"   - '📊 Parâmetros recebidos'")
    print(f"   - 'visual_analysis preview'")

if __name__ == "__main__":
    main()
