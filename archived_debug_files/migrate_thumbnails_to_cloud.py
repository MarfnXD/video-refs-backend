"""
Migrar thumbnails do Instagram CDN para Supabase Storage

Encontra bookmarks com cloud_thumbnail_url apontando para Instagram/TikTok
e faz upload para nosso Supabase Storage.
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from services.thumbnail_service import ThumbnailService

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
thumbnail_service = ThumbnailService(supabase_client=supabase)


async def migrate_thumbnails():
    """Migra todas as thumbnails que ainda estão em CDN externo"""

    print("=" * 80)
    print("MIGRAÇÃO DE THUMBNAILS PARA SUPABASE STORAGE")
    print("=" * 80)
    print()

    # Buscar bookmarks completed com cloud_thumbnail_url
    response = supabase.table('bookmarks') \
        .select('id, user_id, cloud_thumbnail_url') \
        .eq('processing_status', 'completed') \
        .not_.is_('cloud_thumbnail_url', 'null') \
        .execute()

    all_bookmarks = response.data
    print(f"📊 Total de bookmarks: {len(all_bookmarks)}")

    # Filtrar apenas os que têm URL externa (Instagram/TikTok/etc)
    external_domains = ['instagram.com', 'cdninstagram.com', 'tiktok.com', 'muscdn.com']

    to_migrate = []
    for bm in all_bookmarks:
        url = bm['cloud_thumbnail_url']
        if any(domain in url for domain in external_domains):
            to_migrate.append(bm)

    print(f"📸 Thumbnails em CDN externo: {len(to_migrate)}")
    print()

    if not to_migrate:
        print("✅ Todas as thumbnails já estão no Supabase Storage!")
        return

    # Migrar uma por uma
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }

    for idx, bm in enumerate(to_migrate, 1):
        bookmark_id = bm['id']
        user_id = bm['user_id']
        external_url = bm['cloud_thumbnail_url']

        print(f"[{idx}/{len(to_migrate)}] {bookmark_id[:8]}...")
        print(f"            De: {external_url[:70]}...")

        try:
            # Upload para Supabase Storage
            cloud_url = await thumbnail_service.upload_thumbnail(
                thumbnail_url=external_url,
                user_id=user_id,
                bookmark_id=bookmark_id
            )

            if cloud_url:
                # Atualizar bookmark com nova URL
                supabase.table('bookmarks').update({
                    'cloud_thumbnail_url': cloud_url
                }).eq('id', bookmark_id).execute()

                print(f"            Para: {cloud_url[:70]}...")
                print(f"            ✅ Migrado com sucesso")
                results['success'] += 1
            else:
                print(f"            ❌ Upload retornou None")
                results['failed'] += 1
                results['errors'].append({
                    'bookmark_id': bookmark_id,
                    'error': 'Upload returned None'
                })

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"            ❌ Erro: {error_msg}")
            results['failed'] += 1
            results['errors'].append({
                'bookmark_id': bookmark_id,
                'error': error_msg
            })

        print()

    # Resumo
    print("=" * 80)
    print("📊 RESUMO")
    print("=" * 80)
    print(f"✅ Migrados com sucesso: {results['success']}/{len(to_migrate)}")
    print(f"❌ Falhas: {results['failed']}")

    if results['errors']:
        print()
        print("❌ ERROS:")
        for err in results['errors']:
            print(f"   - {err['bookmark_id'][:8]}: {err['error']}")

    print()
    print("✅ MIGRAÇÃO CONCLUÍDA!")


if __name__ == '__main__':
    asyncio.run(migrate_thumbnails())
