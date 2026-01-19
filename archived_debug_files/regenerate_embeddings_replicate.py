"""
Regenera embeddings usando Replicate Multilingual E5 Large.

Substitui os embeddings antigos (OpenAI 1536 dims) por novos (E5 1024 dims).
"""

import asyncio
import os
import json
from dotenv import load_dotenv
from supabase import create_client
import replicate
from tqdm import tqdm
import time

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar no .env!")

if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN deve estar no .env!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)


def generate_embedding_replicate(text: str) -> list[float]:
    """Gera embedding usando Replicate Multilingual E5 Large."""
    output = replicate_client.run(
        "beautyyuyanli/multilingual-e5-large",  # Usa versão mais recente automaticamente
        input={"texts": json.dumps([text])}
    )

    # Output é um generator, consumir e pegar primeiro embedding
    embeddings = list(output)
    if not embeddings or len(embeddings) == 0:
        raise ValueError("Replicate não retornou embeddings")

    return embeddings[0]  # 1024 dims


def create_search_text(bookmark: dict) -> str:
    """Cria texto para embedding (mesma lógica do script anterior)."""
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


def regenerate_all_embeddings():
    """Regenera embeddings de todos os bookmarks usando Replicate E5 Large."""
    print("🔍 Buscando bookmarks no Supabase...")

    response = supabase.table('bookmarks').select('*').execute()
    bookmarks = response.data

    print(f"📊 Total de bookmarks: {len(bookmarks)}")
    print(f"💰 Custo estimado: ~${len(bookmarks) * 0.0005:.4f} USD (Replicate E5)")
    print(f"🌍 Modelo: Multilingual E5 Large (suporta 100 idiomas, incluindo português)\n")

    # Auto-continuar (sem confirmação manual)
    # input("Pressione ENTER para continuar...")

    success_count = 0
    error_count = 0

    for bookmark in tqdm(bookmarks, desc="Regenerando embeddings"):
        try:
            # Cria texto para embedding
            search_text = create_search_text(bookmark)

            if not search_text.strip():
                print(f"\n⚠️ Pulando bookmark sem texto: {bookmark['url']}")
                continue

            # Gera embedding com Replicate
            embedding = generate_embedding_replicate(search_text)

            # Atualiza no Supabase
            supabase.table('bookmarks').update({
                'embedding': embedding
            }).eq('id', bookmark['id']).execute()

            success_count += 1

            # Rate limiting: Replicate tem limites generosos, mas vamos ser conservadores
            time.sleep(0.5)  # 2 req/s

        except Exception as e:
            error_count += 1
            print(f"\n❌ Erro em {bookmark['url']}: {e}")

    print(f"\n✅ Concluído!")
    print(f"   - Sucesso: {success_count}")
    print(f"   - Erros: {error_count}")
    print(f"   - Total: {len(bookmarks)}")


if __name__ == "__main__":
    print("🔄 Regenerando embeddings com Replicate Multilingual E5 Large\n")
    regenerate_all_embeddings()
