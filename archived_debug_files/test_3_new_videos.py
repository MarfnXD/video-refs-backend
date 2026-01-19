"""
Testar cadastro de 3 vídeos novos para verificar se thumbnail
está sendo salva corretamente no Supabase Storage
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BACKEND_URL = 'https://video-refs-backend.onrender.com'
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3 URLs de teste (Instagram Reels novos)
test_urls = [
    'https://www.instagram.com/reel/DGZM8tTRVDp/',  # Design/UI
    'https://www.instagram.com/reel/DGYkQk4x9fG/',  # Tech/AI
    'https://www.instagram.com/reel/DGXvWZ0xLMm/',  # Creative
]

print("=" * 80)
print("TESTE: CADASTRO DE 3 VÍDEOS NOVOS")
print("Objetivo: Verificar se cloud_thumbnail_url aponta para Supabase Storage")
print("=" * 80)
print()

bookmark_ids = []

for idx, url in enumerate(test_urls, 1):
    print(f"[{idx}/3] Cadastrando vídeo...")
    print(f"        URL: {url}")

    # Criar bookmark
    bookmark_data = {
        'url': url,
        'title': f'Teste Thumbnail {idx}',
        'platform': 'instagram',
        'user_id': USER_ID,
        'processing_status': 'queued',
    }

    try:
        result = supabase.table('bookmarks').insert(bookmark_data).execute()
        bookmark_id = result.data[0]['id']
        bookmark_ids.append(bookmark_id)

        print(f"        ✅ Bookmark criado: {bookmark_id}")

        # Chamar backend para processar
        try:
            response = requests.post(
                f'{BACKEND_URL}/api/process-bookmark-complete',
                json={
                    'bookmark_id': bookmark_id,
                    'url': url,
                    'user_id': USER_ID,
                    'extract_metadata': True,
                    'analyze_video': False,  # Pular análise Gemini para testar mais rápido
                    'process_ai': False,     # Pular Claude também
                    'upload_to_cloud': False, # Só queremos testar thumbnail
                    'user_context': None,
                },
                timeout=120  # Timeout maior para dar tempo do upload
            )

            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data.get('job_id', 'N/A')[:8]
                print(f"        🚀 Enfileirado: job {job_id}...")
                print(f"        ⏳ Aguardando processamento...")
            else:
                print(f"        ❌ Erro HTTP: {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"        ⏱️  Timeout (processa em background)")

        except Exception as e:
            print(f"        ❌ Erro: {str(e)[:50]}")

    except Exception as e:
        print(f"        ❌ Erro ao criar bookmark: {str(e)[:100]}")

    print()

# Aguardar processamento
import time
print("⏳ Aguardando 60 segundos para processamento...")
time.sleep(60)

# Verificar resultados
print()
print("=" * 80)
print("📊 VERIFICANDO RESULTADOS")
print("=" * 80)
print()

success = 0
failed = 0

for idx, bookmark_id in enumerate(bookmark_ids, 1):
    result = supabase.table('bookmarks') \
        .select('id, processing_status, cloud_thumbnail_url, thumbnail') \
        .eq('id', bookmark_id) \
        .execute()

    if result.data:
        bm = result.data[0]
        status = bm['processing_status']
        cloud_thumb = bm.get('cloud_thumbnail_url')
        thumb = bm.get('thumbnail')

        print(f"[{idx}/3] {bookmark_id[:8]}...")
        print(f"        Status: {status}")
        print(f"        Thumbnail original: {thumb[:60] if thumb else 'N/A'}...")

        if cloud_thumb:
            is_supabase = 'supabase.co' in cloud_thumb
            is_instagram = 'instagram.com' in cloud_thumb or 'cdninstagram.com' in cloud_thumb

            if is_supabase:
                print(f"        ✅ Cloud Thumbnail: {cloud_thumb[:60]}...")
                print(f"        ✅ CORRETO - Supabase Storage")
                success += 1
            elif is_instagram:
                print(f"        ❌ Cloud Thumbnail: {cloud_thumb[:60]}...")
                print(f"        ❌ ERRO - Instagram CDN (deveria ser Supabase!)")
                failed += 1
            else:
                print(f"        ⚠️  Cloud Thumbnail: {cloud_thumb[:60]}...")
                print(f"        ⚠️  OUTRO DOMÍNIO")
        else:
            print(f"        ⚠️  Cloud Thumbnail: N/A (ainda processando?)")

        print()

print("=" * 80)
print(f"✅ Corretos (Supabase): {success}/3")
print(f"❌ Errados (Instagram): {failed}/3")
print()

if success == 3:
    print("🎉 TESTE PASSOU! Thumbnails sendo salvas corretamente no Supabase Storage!")
elif failed > 0:
    print("❌ TESTE FALHOU! Ainda tem thumbnails sendo salvas com URL do Instagram!")
else:
    print("⏳ Processamento ainda em andamento. Execute o script novamente em alguns minutos.")

# Salvar IDs para cleanup posterior
with open('test_3_videos_bookmark_ids.txt', 'w') as f:
    for bid in bookmark_ids:
        f.write(f"{bid}\n")

print()
print(f"📝 IDs salvos em: test_3_videos_bookmark_ids.txt")
