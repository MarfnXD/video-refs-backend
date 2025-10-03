"""
Regenera embeddings usando OpenAI API (text-embedding-3-small).

Substitui os embeddings gerados por sentence-transformers.
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv
from supabase import create_client
from tqdm import tqdm
import time

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar no .env!")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY deve estar no .env!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


async def generate_embedding_openai(text: str) -> list[float]:
    """Gera embedding usando OpenAI API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "text-embedding-3-small",
                "input": text
            },
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


def create_search_text(bookmark: dict) -> str:
    """Cria texto para embedding (mesma lógica do generate_embeddings_local.py)."""
    parts = []

    # Título
    if bookmark.get('title'):
        parts.append(bookmark['title'])

    # Descrição automática
    if bookmark.get('auto_description'):
        parts.append(bookmark['auto_description'])

    # Contexto processado pela IA
    if bookmark.get('user_context_processed'):
        parts.append(bookmark['user_context_processed'])

    # Tags (manual + auto)
    all_tags = []
    if bookmark.get('tags'):
        all_tags.extend(bookmark['tags'])
    if bookmark.get('auto_tags'):
        all_tags.extend(bookmark['auto_tags'])
    if all_tags:
        parts.append(' '.join(all_tags))

    # Categorias (manual + auto)
    all_categories = []
    if bookmark.get('categories'):
        all_categories.extend(bookmark['categories'])
    if bookmark.get('auto_categories'):
        all_categories.extend(bookmark['auto_categories'])
    if all_categories:
        parts.append(' '.join(all_categories))

    return ' '.join(parts)


async def regenerate_all_embeddings():
    """Regenera embeddings de todos os bookmarks usando OpenAI."""
    print("🔍 Buscando bookmarks no Supabase...")

    response = supabase.table('bookmarks').select('*').execute()
    bookmarks = response.data

    print(f"📊 Total de bookmarks: {len(bookmarks)}")
    print(f"💰 Custo estimado: ${len(bookmarks) * 0.000002:.6f} USD\n")

    input("Pressione ENTER para continuar...")

    success_count = 0
    error_count = 0

    for bookmark in tqdm(bookmarks, desc="Regenerando embeddings"):
        try:
            # Cria texto para embedding
            search_text = create_search_text(bookmark)

            if not search_text.strip():
                print(f"\n⚠️ Pulando bookmark sem texto: {bookmark['url']}")
                continue

            # Gera embedding com OpenAI
            embedding = await generate_embedding_openai(search_text)

            # Atualiza no Supabase
            supabase.table('bookmarks').update({
                'embedding': embedding
            }).eq('id', bookmark['id']).execute()

            success_count += 1

            # Rate limiting: max 500 req/min = ~1 req a cada 120ms
            await asyncio.sleep(0.15)

        except Exception as e:
            error_count += 1
            print(f"\n❌ Erro em {bookmark['url']}: {e}")

    print(f"\n✅ Concluído!")
    print(f"   - Sucesso: {success_count}")
    print(f"   - Erros: {error_count}")
    print(f"   - Total: {len(bookmarks)}")


if __name__ == "__main__":
    print("🔄 Regenerando embeddings com OpenAI API\n")
    asyncio.run(regenerate_all_embeddings())
