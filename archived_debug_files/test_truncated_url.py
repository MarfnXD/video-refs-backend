"""
Testa se as URLs truncadas realmente funcionam
"""
import httpx
import asyncio

# URL truncada de exemplo (Fortnite x Messi)
TRUNCATED_URL = "https://twwpcnyqpwznzarguzit.supabase.co/storage/v1/object/public/thumbnails/53f1ddf2f5c3.jpg"

# URL completa esperada
FULL_URL = "https://twwpcnyqpwznzarguzit.supabase.co/storage/v1/object/sign/thumbnails/0ed9bb40-0041-4dca-9649-256cb418f403/thumbnails/f49ad048-d3b8-4669-b3f8-113c66a382f5.jpg"

async def test_urls():
    print("=" * 80)
    print("🧪 TESTANDO URLs TRUNCADAS vs COMPLETAS")
    print("=" * 80)
    print()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Testar truncada
        print("📸 Testando URL TRUNCADA...")
        print(f"   {TRUNCATED_URL}")
        try:
            response = await client.get(TRUNCATED_URL)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ FUNCIONA! Tamanho: {len(response.content) / 1024:.1f}KB")
            else:
                print(f"   ❌ Erro: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")
        
        print()
        
        # Testar completa (se tiver)
        print("📸 Testando URL COMPLETA...")
        print(f"   {FULL_URL[:80]}...")
        try:
            response = await client.get(FULL_URL)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ FUNCIONA! Tamanho: {len(response.content) / 1024:.1f}KB")
            else:
                print(f"   ❌ Erro: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_urls())
