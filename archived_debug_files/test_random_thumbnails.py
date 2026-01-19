"""
Testa 10 URLs aleatórias das "truncadas" para ver se realmente funcionam
"""
import os
import httpx
import asyncio
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def test():
    print("=" * 80)
    print("🧪 TESTANDO 10 THUMBNAILS ALEATÓRIAS")
    print("=" * 80)
    print()
    
    # Buscar bookmarks com URLs "public"
    result = supabase.table('bookmarks')\
        .select('id, smart_title, cloud_thumbnail_url')\
        .eq('user_id', USER_ID)\
        .like('cloud_thumbnail_url', '%/object/public/thumbnails/%')\
        .limit(10)\
        .execute()
    
    bookmarks = result.data or []
    
    print(f"Testando {len(bookmarks)} thumbnails...")
    print()
    
    working = 0
    broken = 0
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for idx, bm in enumerate(bookmarks, 1):
            title = bm.get('smart_title', 'Sem título')[:40]
            url = bm.get('cloud_thumbnail_url')
            
            try:
                response = await client.get(url)
                
                if response.status_code == 200:
                    print(f"[{idx}] ✅ {title}...")
                    working += 1
                else:
                    print(f"[{idx}] ❌ {title}... (Status {response.status_code})")
                    broken += 1
                    
            except Exception as e:
                print(f"[{idx}] ❌ {title}... (Erro: {str(e)[:50]})")
                broken += 1
    
    print()
    print("=" * 80)
    print(f"✅ Funcionando: {working}/{len(bookmarks)} ({working*100//len(bookmarks) if len(bookmarks) > 0 else 0}%)")
    print(f"❌ Quebradas: {broken}/{len(bookmarks)} ({broken*100//len(bookmarks) if len(bookmarks) > 0 else 0}%)")
    print()
    
    if working >= len(bookmarks) * 0.8:
        print("✅ Maioria FUNCIONA! As URLs 'public' estão corretas.")
        print("   O problema da Red Bull é isolado.")
    else:
        print("❌ Maioria QUEBRADA. Há problema generalizado.")

if __name__ == "__main__":
    asyncio.run(test())
