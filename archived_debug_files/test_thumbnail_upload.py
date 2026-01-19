"""
Teste isolado do upload de thumbnail
Para diagnosticar o problema das URLs truncadas
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from services.thumbnail_service import ThumbnailService

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# URL de thumbnail de teste do Instagram
TEST_THUMBNAIL_URL = "https://scontent-atl3-2.cdninstagram.com/v/t51.2885-15/503916979_1475446710091492_9111351887303849073_n.jpg"
TEST_USER_ID = "0ed9bb40-0041-4dca-9649-256cb418f403"
TEST_BOOKMARK_ID = "test-thumbnail-debug-001"

async def test_upload():
    print("=" * 80)
    print("🧪 TESTE DE UPLOAD DE THUMBNAIL")
    print("=" * 80)
    print()
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    thumbnail_service = ThumbnailService(supabase)
    
    print(f"Thumbnail URL: {TEST_THUMBNAIL_URL[:80]}...")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Bookmark ID: {TEST_BOOKMARK_ID}")
    print()
    
    print("⏳ Fazendo upload...")
    print()
    
    try:
        result = await thumbnail_service.upload_thumbnail(
            thumbnail_url=TEST_THUMBNAIL_URL,
            user_id=TEST_USER_ID,
            bookmark_id=TEST_BOOKMARK_ID
        )
        
        print()
        print("=" * 80)
        print("📊 RESULTADO")
        print("=" * 80)
        print()
        
        if result:
            print(f"✅ Upload bem-sucedido!")
            print()
            print(f"URL retornada:")
            print(f"  {result}")
            print()
            
            # Verificar se a URL está completa
            expected_path = f"{TEST_USER_ID}/thumbnails/{TEST_BOOKMARK_ID}"
            
            if expected_path in result:
                print("✅ URL está COMPLETA (contém user_id e bookmark_id)")
            else:
                print("❌ URL está TRUNCADA/INCORRETA")
                print(f"   Esperado conter: {expected_path}")
            
            print()
            
            # Verificar formato
            if '/sign/' in result:
                print("✅ Formato: Signed URL")
            elif '/public/' in result:
                print("⚠️  Formato: Public URL (não deveria)")
            else:
                print("❌ Formato: Desconhecido")
                
        else:
            print("❌ Upload FALHOU (retornou None)")
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_upload())
