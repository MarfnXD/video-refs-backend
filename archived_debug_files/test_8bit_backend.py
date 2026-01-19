"""
Script para testar o endpoint /api/process-metadata-auto
com os dados reais do bookmark "8-Bit Spill"
"""
import requests
import json

# Dados reais do bookmark "8-Bit Spill" do Supabase
bookmark_data = {
    "title": "8-Bit Spill\n\nAhhh I've been wanting to do this animation for a bit now and I just the workflow down",
    "description": "Ahhh I've been wanting to do this animation for a bit now and I just the workflow down",
    "hashtags": [],  # Vazio
    "top_comments": [
        {"text": "this is so cool", "likes": 150},
        {"text": "amazing work!", "likes": 120},
        {"text": "how did you do this?", "likes": 100},
        {"text": "pixel art is so underrated", "likes": 90},
        {"text": "love the animation", "likes": 80},
        {"text": "great job!", "likes": 70},
        {"text": "this is fire", "likes": 60},
        {"text": "keep it up", "likes": 50},
        {"text": "so smooth", "likes": 40},
        {"text": "perfection", "likes": 30}
    ],
    # cloud_video_url ausente (não tem vídeo baixado)
}

print("="*80)
print("🧪 TESTANDO BACKEND: /api/process-metadata-auto")
print("="*80)
print("\n📤 DADOS ENVIADOS:")
print(json.dumps(bookmark_data, indent=2, ensure_ascii=False))

# Backend em produção
backend_url = "https://video-refs-backend.onrender.com/api/process-metadata-auto"

print(f"\n🌐 URL: {backend_url}")
print("⏳ Enviando requisição...")

try:
    response = requests.post(
        backend_url,
        json=bookmark_data,
        timeout=150  # Mesmo timeout do app
    )

    print(f"\n📥 RESPOSTA DO BACKEND:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")

    if response.status_code == 200:
        try:
            data = response.json()
            print(f"\n✅ JSON VÁLIDO:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # Análise detalhada
            print(f"\n🔍 ANÁLISE DETALHADA:")
            print(f"   success: {data.get('success')}")
            print(f"   auto_description: {data.get('auto_description', 'N/A')[:100]}...")
            print(f"   auto_tags: {data.get('auto_tags', [])} ({len(data.get('auto_tags', []))} tags)")
            print(f"   auto_categories: {data.get('auto_categories', [])} ({len(data.get('auto_categories', []))} cats)")
            print(f"   relevance_score: {data.get('relevance_score', 'N/A')}")

        except json.JSONDecodeError as e:
            print(f"❌ ERRO AO DECODIFICAR JSON: {e}")
            print(f"   Body (raw): {response.text[:500]}")
    else:
        print(f"\n❌ ERRO HTTP {response.status_code}")
        print(f"   Body: {response.text}")

except requests.exceptions.Timeout:
    print("\n⏱️ TIMEOUT: Backend demorou mais de 150 segundos")
except requests.exceptions.RequestException as e:
    print(f"\n❌ ERRO NA REQUISIÇÃO: {e}")
except Exception as e:
    print(f"\n❌ ERRO INESPERADO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ TESTE CONCLUÍDO")
print("="*80)
