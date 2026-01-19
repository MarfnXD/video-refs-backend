#!/usr/bin/env python3
"""
Script de teste para debugar Gemini 3 Pro (problema de resposta vazia)
"""
import requests
import time

# Config
BACKEND_URL = "https://video-refs-backend.onrender.com"

# Bookmark de teste que já existe (Monsters Inc)
BOOKMARK_ID = "c3b11529-a446-429d-ad4c-a97fe072fbc5"
USER_ID = "0ed9bb40-0041-4dca-9649-256cb418f403"
TEST_URL = "https://www.instagram.com/reel/DR-NF7DjdvN/"

def main():
    print("🔮 TESTE DEBUG: Gemini 3 Pro - Investigar resposta vazia")
    print("=" * 80)
    print(f"Bookmark ID: {BOOKMARK_ID}")
    print(f"URL: {TEST_URL}")
    print()
    print("🎯 OBJETIVO:")
    print("   Verificar os logs DEBUG para entender por que Gemini 3 Pro retorna vazio")
    print()

    # Chamar endpoint de processamento
    print("📡 Chamando endpoint de processamento...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/process-bookmark-complete",
            json={
                "bookmark_id": BOOKMARK_ID,
                "user_id": USER_ID,
                "url": TEST_URL,
                "upload_to_cloud": True,
                "process_ai": True
            },
            timeout=10
        )

        print(f"✅ Status: {response.status_code}")
        print(f"📄 Response: {response.json()}")
    except Exception as e:
        print(f"⚠️  Erro ao chamar endpoint: {e}")
        print("(Isso é normal se Render estava dormindo)")

    print("\n⏳ Aguardando processamento (~60-90 segundos)...")
    print("   Apify → Upload → Gemini 2.5 Flash → Gemini 3 Pro")
    print()
    print("=" * 80)
    print("🔍 ABRA OS LOGS DO RENDER AGORA:")
    print("   https://dashboard.render.com/web/srv-cpgd7iu8ii6s73a0pq6g/logs")
    print("=" * 80)
    print()
    print("📝 PROCURE POR ESTES LOGS DEBUG (ordem esperada):")
    print()
    print("1️⃣  GEMINI 2.5 FLASH (análise de vídeo):")
    print("   ✅ '🎬 Analisando vídeo com Gemini Flash 2.5'")
    print("   ✅ '✅ Vídeo analisado com sucesso'")
    print()
    print("2️⃣  GEMINI 3 PRO (processamento final):")
    print("   ✅ '🔮 Chamando Gemini 3 Pro (auto) com thinking_level=high...'")
    print("   🔍 '🔍 DEBUG (auto) - Tipo de output: <class ...>'")
    print("   🔍 '🔍 DEBUG (auto) - Output object: ...'")
    print("   🔍 '🔍 DEBUG (auto) - Chunk 1: <class ...> = ...'")
    print("   🔍 '✅ DEBUG (auto) - Total de chunks: N, texto final: M chars'")
    print()
    print("3️⃣  ANÁLISE DOS LOGS:")
    print("   ❓ Se 'Total de chunks: 0' → output está vazio desde o início")
    print("   ❓ Se 'Total de chunks: N > 0' → chunks existem mas estão vazios")
    print("   ❓ Verificar 'Tipo de output' - deve ser iterator ou similar")
    print()
    print("=" * 80)

    print("\n⏱️  Aguardando 90 segundos para processamento...")
    for i in range(18):
        time.sleep(5)
        print(f"   {(i+1)*5}s...", end=" ", flush=True)
        if (i+1) % 6 == 0:
            print()  # Nova linha a cada 30s

    print("\n\n✅ Tempo de espera completo!")
    print()
    print("🔍 PRÓXIMO PASSO:")
    print("   1. Vá aos logs do Render")
    print("   2. Encontre os logs DEBUG acima")
    print("   3. Verifique:")
    print("      - Tipo de output (deve ser iterator)")
    print("      - Quantos chunks foram retornados")
    print("      - Conteúdo de cada chunk")
    print("   4. Com essas informações, vamos entender o problema!")

if __name__ == "__main__":
    main()
