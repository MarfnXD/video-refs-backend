"""
Script para migrar thumbnails do Instagram/TikTok para Supabase Storage
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from services.thumbnail_service import ThumbnailService

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

async def migrate_thumbnails():
    # Buscar bookmarks com URLs do Instagram
    result = supabase.table('bookmarks').select('id, user_id, smart_title, cloud_thumbnail_url').execute()
    
    instagram_items = [
        item for item in result.data 
        if item.get('cloud_thumbnail_url') and (
            'instagram' in item['cloud_thumbnail_url'] or 
            'tiktok' in item['cloud_thumbnail_url'] or
            'cdninstagram' in item['cloud_thumbnail_url']
        )
    ]
    
    print(f"Encontrados {len(instagram_items)} bookmarks com URLs do Instagram/TikTok")
    print("=" * 80)
    
    thumbnail_service = ThumbnailService(supabase)
    
    success_count = 0
    fail_count = 0
    
    for i, item in enumerate(instagram_items, 1):
        print(f"\n[{i}/{len(instagram_items)}] {item['smart_title'][:60]}")
        print(f"  URL atual: {item['cloud_thumbnail_url'][:80]}...")
        
        try:
            # Upload para Supabase Storage
            new_url = await thumbnail_service.upload_thumbnail(
                thumbnail_url=item['cloud_thumbnail_url'],
                user_id=item['user_id'],
                bookmark_id=item['id']
            )
            
            if new_url:
                # Atualizar no banco
                supabase.table('bookmarks').update({
                    'cloud_thumbnail_url': new_url
                }).eq('id', item['id']).execute()
                
                print(f"  ✅ Migrado com sucesso!")
                print(f"  Nova URL: {new_url[:80]}...")
                success_count += 1
            else:
                print(f"  ❌ Falha no upload")
                fail_count += 1
                
        except Exception as e:
            print(f"  ❌ Erro: {str(e)[:100]}")
            fail_count += 1
    
    print("\n" + "=" * 80)
    print(f"Resumo: {success_count} migrados, {fail_count} falhas")

if __name__ == "__main__":
    asyncio.run(migrate_thumbnails())
