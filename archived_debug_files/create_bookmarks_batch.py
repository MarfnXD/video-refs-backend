#!/usr/bin/env python3
"""
Script para criar múltiplos bookmarks e processar automaticamente
"""
import os
import requests
import time
from datetime import datetime

# Config
BACKEND_URL = "https://video-refs-backend.onrender.com"
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = "0ed9bb40-0041-4dca-9649-256cb418f403"  # Marco

# Lista de URLs para criar bookmarks
BOOKMARKS = [
    # Dezembro 2024
    {"date": "24/12", "url": "https://www.instagram.com/reel/DSkEAeHjcp4/?igsh=aXZ3ZWM4d3d5cnBm"},
    {"date": "24/12", "url": "https://www.instagram.com/p/DSlqss8FDBb/?igsh=MWxrazVkcnQ2ZWYzYg=="},
    {"date": "16/12", "url": "https://vt.tiktok.com/ZSP54yGKh/"},
    {"date": "16/12", "url": "https://vt.tiktok.com/ZSP5QJ76N/"},
    {"date": "16/12", "url": "https://vt.tiktok.com/ZSP59X7q3/"},
    {"date": "16/12", "url": "https://www.instagram.com/p/DSU0hkZjpnr/"},
    {"date": "09/12", "url": "https://www.instagram.com/reel/DSDAvayDbpl/?igsh=M2VyMnF1aGhubXhv"},
    {"date": "09/12", "url": "https://www.instagram.com/reel/DSDSW5tkXJz/?igsh=bHF2OHUwZXF2djUz"},
    {"date": "07/12", "url": "https://www.instagram.com/p/DR5_0l3k-ko/?img_index=4&igsh=aWJjNHhlc2RmbjVx"},

    # Novembro 2025
    {"date": "26/11", "url": "https://www.instagram.com/stories/rodrigosotero/3774721298329863106"},
    {"date": "13/11", "url": "https://www.instagram.com/reel/DM7wIS3S0vN/?igsh=MWJlN2lycm44ejhxbQ=="},
    {"date": "11/11", "url": "https://www.instagram.com/reel/C15X3lGvbwt/"},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DD5SQ98y1Gn/"},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DGsXZIJoHvS/"},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DIqBFLUNzbu/"},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DJvEm76KiBs/"},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DIR39Pqh3JO/"},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DOgwWELDzRf/?igsh=MXR4Y2h5MHI1cWtraQ=="},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DQo6-ruEc03/?igsh=Z2NpejFxenpubjYx"},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DOjoL5yjm7U/?igsh=MTl4eG9qMnNuOTgxag=="},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DPWcu-ljdcM/?igsh=MTQ3bTNxd3UycGF3cA=="},
    {"date": "11/11", "url": "https://www.instagram.com/reel/DMv72D-T65t/?igsh=MWttZzU5d2ZtcWxpeA=="},
    {"date": "10/11", "url": "https://www.instagram.com/reel/DOgwWELDzRf/?igsh=MXR4Y2h5MHI1cWtraQ=="},
    {"date": "02/11", "url": "https://www.instagram.com/reel/DQHxhBfAY5W/?igsh=OHQ4d2RsMDNnd2R1"},

    # Outubro 2025
    {"date": "31/10", "url": "https://www.instagram.com/p/DPq5fgKiPr2/?igsh=cWgxamJwNHpkc254"},
    {"date": "30/10", "url": "https://www.instagram.com/reel/DQHINw7AP2l/?igsh=cGZtMm1ienNnNW93"},
    {"date": "29/10", "url": "https://www.instagram.com/reel/DQUThmfDanm/?igsh=MXUxZnZzMnNvdnRjdQ=="},
    {"date": "29/10", "url": "https://www.instagram.com/reel/DPw6GhFj0g1/?igsh=YWFqb2YxdWU2emU5"},
    {"date": "28/10", "url": "https://www.instagram.com/reel/DQMLl43EUje/?igsh=bmhrY2wwd3R4eXRp"},
    {"date": "28/10", "url": "https://www.instagram.com/reel/DNu_MNf2kr7/?igsh=c2FwZDE5ZTdveTgw"},
    {"date": "28/10", "url": "https://www.instagram.com/reel/DQHH9M6CFdL/?igsh=YmZib2duOHZ2aTlh"},
    {"date": "28/10", "url": "https://www.instagram.com/reel/DQVCMhTCWRF/?igsh=NjNjdGRlN25hZHV6"},
    {"date": "17/10", "url": "https://www.instagram.com/reel/DP1UqsiieYI/?igsh=bWVoZmppaHpmNzc3"},
]

def detect_platform(url):
    """Detecta plataforma pela URL"""
    if 'tiktok.com' in url:
        return 'tiktok'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    return 'unknown'

def create_bookmark_in_supabase(url, date_str):
    """Cria bookmark no Supabase"""
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }

    platform = detect_platform(url)

    data = {
        'user_id': USER_ID,
        'url': url,
        'title': f'Video {date_str}',
        'platform': platform,
        'processing_status': 'queued',
    }

    try:
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/bookmarks',
            headers=headers,
            json=data
        )

        if response.status_code == 201:
            bookmark = response.json()[0]
            return bookmark['id'], True
        elif response.status_code == 409:
            # Duplicata - já existe
            print(f"   ⚠️  Já existe bookmark com essa URL")
            return None, False
        else:
            print(f"   ❌ Erro ao criar: {response.status_code} - {response.text}")
            return None, False
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return None, False

def process_bookmark_backend(bookmark_id, url):
    """Processa bookmark via endpoint backend"""
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/process-bookmark-complete',
            json={
                'bookmark_id': bookmark_id,
                'url': url,
                'user_id': USER_ID,
                'extract_metadata': True,
                'analyze_video': True,
                'process_ai': True,
                'upload_to_cloud': True,
            },
            timeout=10
        )

        if response.status_code == 200 and response.json().get('success'):
            print(f"   ✅ Enviado para processamento (job_id: {response.json().get('job_id')})")
            return True
        else:
            print(f"   ⚠️  Falha ao processar: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ⚠️  Erro ao processar: {e}")
        return False

def main():
    print("📚 CRIAÇÃO EM LOTE DE BOOKMARKS")
    print("=" * 80)
    print(f"Total de URLs: {len(BOOKMARKS)}")
    print(f"Usuário: {USER_ID} (Marco)")
    print()

    created_count = 0
    duplicate_count = 0
    error_count = 0
    processed_count = 0

    for i, item in enumerate(BOOKMARKS, 1):
        url = item['url']
        date_str = item['date']

        print(f"[{i}/{len(BOOKMARKS)}] {date_str} - {url[:60]}...")

        # 1. Criar bookmark no Supabase
        bookmark_id, is_new = create_bookmark_in_supabase(url, date_str)

        if bookmark_id:
            created_count += 1

            # 2. Processar via backend (em background)
            if process_bookmark_backend(bookmark_id, url):
                processed_count += 1
        elif not is_new:
            duplicate_count += 1
        else:
            error_count += 1

        # Delay para não sobrecarregar
        time.sleep(0.5)

    print()
    print("=" * 80)
    print("📊 RESUMO:")
    print(f"   ✅ Criados: {created_count}")
    print(f"   📤 Enviados para processamento: {processed_count}")
    print(f"   ⚠️  Duplicatas (já existiam): {duplicate_count}")
    print(f"   ❌ Erros: {error_count}")
    print()
    print("⏳ PROCESSAMENTO EM BACKGROUND:")
    print("   Os bookmarks estão sendo processados pelo backend agora.")
    print("   Isso pode demorar alguns minutos (Apify + Upload + Gemini 2.5 + Gemini 3)")
    print("   Você pode acompanhar no app via Realtime updates!")

if __name__ == "__main__":
    main()
