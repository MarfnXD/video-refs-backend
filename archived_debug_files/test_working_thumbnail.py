"""
Testa upload com uma thumbnail que FUNCIONOU
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from services.thumbnail_service import ThumbnailService

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Thumbnail de um bookmark que FUNCIONOU (ID: 88788190-2bf6-474c-9391-60bc63c6c8ec)
WORKING_THUMBNAIL_URL = "https://scontent-lax3-2.cdninstagram.com/v/t51.2885-15/468107929_1790696027106064_8531896068992327028_n.jpg"
TEST_USER_ID = "0ed9bb40-0041-4dca-9649-256cb418f403"
TEST_BOOKMARK_ID = "test-working-thumb-002"

async def test_upload():
    print("=" * 80)
    print("🧪 TESTE COM THUMBNAIL QUE FUNCIONOU")
    print("=" * 80)
    print()
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    thumbnail_service = ThumbnailService(supabase)
    
    print(f"Thumbnail URL: {WORKING_THUMBNAIL_URL}")
    print()
    
    try:
        result = await thumbnail_service.upload_thumbnail(
            thumbnail_url=WORKING_THUMBNAIL_URL,
            user_id=TEST_USER_ID,
            bookmark_id=TEST_BOOKMARK_ID
        )
        
        print()
        print("=" * 80)
        if result:
            print("✅ SUCESSO!")
            print(f"URL: {result}")
            
            if TEST_USER_ID in result and TEST_BOOKMARK_ID in result:
                print("✅ URL contém user_id e bookmark_id (CORRETO)")
            else:
                print("❌ URL não contém IDs esperados")
        else:
            print("❌ FALHOU (retornou None)")
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_upload())
