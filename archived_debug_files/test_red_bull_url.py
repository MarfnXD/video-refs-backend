"""
Testa especificamente a URL da Red Bull que está quebrada no app
"""
import httpx
import asyncio
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RED_BULL_ID = 'eefc288c-655a-4abb-b1c7-ac79460d3cf6'

async def test():
    print("=" * 80)
    print("🔍 VERIFICANDO RED BULL x ARCANE")
    print("=" * 80)
    print()
    
    result = supabase.table('bookmarks').select('smart_title, cloud_thumbnail_url').eq('id', RED_BULL_ID).single().execute()
    
    data = result.data
    title = data.get('smart_title')
    thumb_url = data.get('cloud_thumbnail_url')
    
    print(f"Título: {title}")
    print(f"Thumbnail URL: {thumb_url}")
    print()
    
    # Testar acesso
    print("📸 Testando acesso à URL...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(thumb_url)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ URL FUNCIONA! Tamanho: {len(response.content) / 1024:.1f}KB")
                print(f"Content-Type: {response.headers.get('content-type')}")
            else:
                print(f"❌ Erro: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Erro ao acessar: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test())
