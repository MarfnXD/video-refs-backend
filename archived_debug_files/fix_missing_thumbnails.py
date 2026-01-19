"""
Script para corrigir bookmarks que estão com cloud_thumbnail_url faltando
Apenas faz upload da thumbnail, sem tocar no vídeo ou análises
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from services.thumbnail_service import ThumbnailService

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
thumbnail_service = ThumbnailService(supabase)

async def fix_missing_thumbnails():
    """
    Busca bookmarks com metadata.thumbnail_url mas sem cloud_thumbnail_url
    e faz upload da thumbnail
    """
    print("=" * 80)
    print("🔧 CORREÇÃO DE THUMBNAILS FALTANDO")
    print("=" * 80)
    print()

    # Buscar bookmarks com problema
    print("🔍 Buscando bookmarks com thumbnail faltando...")

    # Bookmarks que:
    # - Têm metadata com thumbnail_url
    # - NÃO têm cloud_thumbnail_url
    # - Status = completed
    result = supabase.table('bookmarks')\
        .select('id, url, metadata, cloud_thumbnail_url')\
        .eq('user_id', USER_ID)\
        .eq('processing_status', 'completed')\
        .is_('cloud_thumbnail_url', 'null')\
        .execute()

    bookmarks = result.data or []

    # Filtrar só os que têm thumbnail_url no metadata
    bookmarks_to_fix = []
    for bm in bookmarks:
        metadata = bm.get('metadata') or {}
        thumbnail_url = metadata.get('thumbnail_url')
        if thumbnail_url:
            bookmarks_to_fix.append({
                'id': bm['id'],
                'url': bm['url'],
                'thumbnail_url': thumbnail_url
            })

    print(f"✓ Encontrados {len(bookmarks_to_fix)} bookmarks para corrigir")
    print()

    if not bookmarks_to_fix:
        print("✅ Nenhum bookmark precisa de correção!")
        return

    # Mostrar preview
    print("📋 Preview dos primeiros 10:")
    for bm in bookmarks_to_fix[:10]:
        print(f"  - {bm['id'][:8]}... : {bm['url'][:60]}...")
    if len(bookmarks_to_fix) > 10:
        print(f"  ... e mais {len(bookmarks_to_fix) - 10}")
    print()

    # Confirmar
    print(f"⚠️  Vai processar {len(bookmarks_to_fix)} thumbnails.")
    print()

    # Processar
    fixed = 0
    failed = 0

    for idx, bm in enumerate(bookmarks_to_fix, 1):
        bookmark_id = bm['id']
        thumbnail_url = bm['thumbnail_url']

        print(f"[{idx}/{len(bookmarks_to_fix)}] {bookmark_id[:8]}...")

        try:
            # Upload da thumbnail
            cloud_thumbnail_url = await thumbnail_service.upload_thumbnail(
                thumbnail_url=thumbnail_url,
                user_id=USER_ID,
                bookmark_id=bookmark_id
            )

            if cloud_thumbnail_url:
                # Atualizar no banco
                supabase.table('bookmarks')\
                    .update({'cloud_thumbnail_url': cloud_thumbnail_url})\
                    .eq('id', bookmark_id)\
                    .execute()

                print(f"  ✅ OK: {cloud_thumbnail_url[:60]}...")
                fixed += 1
            else:
                print(f"  ❌ Upload falhou (retornou None)")
                failed += 1

        except Exception as e:
            print(f"  ❌ Erro: {str(e)[:80]}")
            failed += 1

        # Delay para não sobrecarregar
        if idx % 10 == 0:
            print()
            await asyncio.sleep(2)

    print()
    print("=" * 80)
    print("📊 RESUMO")
    print("=" * 80)
    print(f"✅ Corrigidos: {fixed}")
    print(f"❌ Falhas: {failed}")
    print()

if __name__ == "__main__":
    asyncio.run(fix_missing_thumbnails())
