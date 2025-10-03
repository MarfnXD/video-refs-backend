"""
Script para extrair thumbnails de bookmarks que não possuem.

Busca bookmarks com thumbnail NULL e extrai usando o Apify Service.
"""
import asyncio
import os
from dotenv import load_dotenv

# IMPORTANTE: Carregar .env ANTES de importar qualquer serviço
load_dotenv()

from supabase import create_client, Client
from services.apify_service import ApifyService

# Configuração
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar definidas!")

# Clientes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
apify_service = ApifyService()


async def extract_missing_thumbnails(limit: int = 100):
    """
    Extrai thumbnails para bookmarks que não possuem.

    Args:
        limit: Quantos bookmarks processar por vez
    """
    print(f"🔍 Buscando bookmarks sem thumbnail...")

    # Busca bookmarks sem thumbnail
    response = supabase.table('bookmarks')\
        .select('id, url, platform, thumbnail')\
        .is_('thumbnail', 'null')\
        .limit(limit)\
        .execute()

    bookmarks = response.data if response.data else []

    if not bookmarks:
        print("✅ Todos os bookmarks já têm thumbnail!")
        return

    print(f"📦 Encontrados {len(bookmarks)} bookmarks sem thumbnail")

    success_count = 0
    error_count = 0

    for i, bookmark in enumerate(bookmarks):
        url = bookmark['url']
        bookmark_id = bookmark['id']
        platform = bookmark['platform']

        print(f"\n[{i+1}/{len(bookmarks)}] Processando: {url[:60]}...")

        try:
            # Extrai metadados (inclui thumbnail)
            metadata = await apify_service.extract_metadata(url)

            if not metadata or not metadata.thumbnail:
                print(f"  ⚠️  Sem thumbnail disponível")
                error_count += 1
                continue

            # Atualiza banco com thumbnail
            supabase.table('bookmarks')\
                .update({'thumbnail': metadata.thumbnail})\
                .eq('id', bookmark_id)\
                .execute()

            print(f"  ✅ Thumbnail extraída: {metadata.thumbnail[:80]}")
            success_count += 1

            # Pausa para não sobrecarregar API
            await asyncio.sleep(2)

        except Exception as e:
            print(f"  ❌ Erro: {e}")
            error_count += 1

    print(f"\n" + "="*60)
    print(f"✅ Sucesso: {success_count}")
    print(f"❌ Erros: {error_count}")
    print(f"📊 Total processado: {len(bookmarks)}")


async def main():
    """Função principal"""
    try:
        # Processa até 50 bookmarks por vez
        await extract_missing_thumbnails(limit=50)
    finally:
        await apify_service.close()


if __name__ == "__main__":
    print("🎬 Extrator de Thumbnails Ausentes")
    print("="*60)
    asyncio.run(main())
