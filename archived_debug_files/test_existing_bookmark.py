#!/usr/bin/env python3
"""
Script de teste usando bookmark existente (mais simples)
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
    print("🧪 TESTE DE FLUXO GEMINI → CLAUDE (Bookmark Existente)")
    print("=" * 80)
    print(f"Bookmark ID: {BOOKMARK_ID}")
    print(f"URL: {TEST_URL}")

    # Chamar endpoint de processamento
    print("\n📡 Chamando endpoint de processamento...")
    response = requests.post(
        f"{BACKEND_URL}/api/process-bookmark-complete",
        json={
            "bookmark_id": BOOKMARK_ID,
            "user_id": USER_ID,
            "url": TEST_URL,
            "upload_to_cloud": True,
            "process_ai": True
        }
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    print("\n⏳ Aguardando processamento (~60-90 segundos)...")
    print("   Apify + Upload + Gemini + Claude")
    print("\n🔍 ABRA OS LOGS DO RENDER AGORA:")
    print("   https://dashboard.render.com/web/srv-cpgd7iu8ii6s73a0pq6g/logs")
    print("\n📝 Procure por esses logs DEBUG:")
    print("   1. '📊 Gemini analysis recebido: [...]'")
    print("   2. '   transcript: XXX chars'")
    print("   3. '   visual_analysis: XXX chars'")
    print("   4. '📝 Timeline extraído: XXX chars'")
    print("   5. '   Preview: [...]'")
    print("   6. '📊 Parâmetros recebidos:'")
    print("   7. '   visual_analysis: XXX chars'")
    print("   8. '   visual_analysis preview: [...]'")

    print("\n⏱️  Aguardando 90 segundos...")
    for i in range(18):
        time.sleep(5)
        print(f"   {(i+1)*5}s...", end=" ", flush=True)
        if (i+1) % 6 == 0:
            print()  # Nova linha a cada 30s

    print("\n\n✅ Teste iniciado!")
    print(f"\n🔍 Agora verifique os logs do Render para ver se:")
    print(f"   1. Gemini retornou visual_analysis com N caracteres")
    print(f"   2. Timeline foi extraído com N caracteres")
    print(f"   3. Claude recebeu visual_analysis com N caracteres")
    print(f"   4. Se N > 0 em todos, mas Claude reclama → problema no prompt")
    print(f"   5. Se N = 0 em algum passo → encontramos onde está vazando!")

if __name__ == "__main__":
    main()
