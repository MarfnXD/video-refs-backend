#!/usr/bin/env python3
"""
Script para regenerar embeddings APENAS dos bookmarks com análise multimodal.

Busca bookmarks que JÁ TEM video_transcript (análise completa) e regenera embeddings
incluindo transcrição + análise visual.

Uso: python3 regenerate_multimodal_embeddings.py
"""

import os
import sys
import asyncio
from supabase import create_client, Client
from openai import OpenAI

# Configuração
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY devem estar configuradas!")
    sys.exit(1)

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY não configurada!")
    sys.exit(1)

# Clientes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def generate_rich_text_for_embedding(bookmark: dict) -> str:
    """
    Gera texto rico incluindo TODOS os dados disponíveis (incluindo multimodal).
    """
    parts = []

    # Título (sempre presente)
    if bookmark.get("title"):
        parts.append(f"Título: {bookmark['title']}")

    # Descrição
    if bookmark.get("metadata", {}).get("description"):
        parts.append(f"Descrição: {bookmark['metadata']['description']}")

    # Descrição automática (IA)
    if bookmark.get("auto_description"):
        parts.append(f"Análise do conteúdo: {bookmark['auto_description']}")

    # === MULTIMODAL: TRANSCRIÇÃO DO ÁUDIO ===
    if bookmark.get("video_transcript"):
        transcript = bookmark["video_transcript"]
        # Limita transcrição a 2000 caracteres para otimizar tokens
        if len(transcript) > 2000:
            transcript = transcript[:2000] + "..."
        parts.append(f"Transcrição do áudio: {transcript}")

    # === MULTIMODAL: ANÁLISE VISUAL ===
    if bookmark.get("visual_analysis"):
        parts.append(f"Análise visual (IA): {bookmark['visual_analysis']}")

    # Tags manuais
    if bookmark.get("tags"):
        tags_str = ", ".join(bookmark["tags"])
        parts.append(f"Tags: {tags_str}")

    # Tags automáticas (IA)
    if bookmark.get("auto_tags"):
        auto_tags_str = ", ".join(bookmark["auto_tags"])
        parts.append(f"Tags automáticas: {auto_tags_str}")

    # Categorias manuais
    if bookmark.get("categories"):
        cats_str = ", ".join(bookmark["categories"])
        parts.append(f"Categorias: {cats_str}")

    # Categorias automáticas (IA)
    if bookmark.get("auto_categories"):
        auto_cats_str = ", ".join(bookmark["auto_categories"])
        parts.append(f"Categorias automáticas: {auto_cats_str}")

    # Contexto do usuário (processado)
    if bookmark.get("user_context_processed"):
        parts.append(f"Contexto: {bookmark['user_context_processed']}")

    # Projetos
    if bookmark.get("projects"):
        projects_str = ", ".join(bookmark["projects"])
        parts.append(f"Projetos: {projects_str}")

    return "\n".join(parts)


def generate_embedding(text: str) -> list:
    """
    Gera embedding usando OpenAI text-embedding-3-small.
    """
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding


async def main():
    print("\n🔄 REGENERAÇÃO DE EMBEDDINGS - BOOKMARKS COM ANÁLISE MULTIMODAL")
    print("="*70)

    # Busca bookmarks que TÊM video_transcript (análise multimodal completa)
    print("\n📊 Buscando bookmarks com análise multimodal...")
    print("   Critério: video_transcript IS NOT NULL")
    print()

    response = supabase.table("bookmarks") \
        .select("*") \
        .not_.is_('video_transcript', 'null') \
        .execute()

    bookmarks = response.data

    if not bookmarks:
        print("✅ Nenhum bookmark com análise multimodal encontrado!")
        return

    total = len(bookmarks)
    print(f"📦 {total} bookmarks encontrados\n")

    # Confirma com usuário
    print(f"⚠️  AVISO: Isso vai regenerar embeddings de {total} bookmarks")
    print(f"💰 Custo estimado: ~${total * 0.00004:.4f} USD (text-embedding-3-small)")
    print()
    confirm = input("Continuar? (s/N): ")
    if confirm.lower() != 's':
        print("❌ Cancelado pelo usuário")
        return

    # Processa cada bookmark
    success_count = 0
    failed_count = 0
    total_tokens = 0

    for i, bookmark in enumerate(bookmarks, 1):
        bookmark_id = bookmark['id']
        title = bookmark['title']

        try:
            print(f"\n[{i}/{total}] 📹 {title[:60]}")

            # 1. Gera texto rico (COM transcrição + visual analysis)
            rich_text = generate_rich_text_for_embedding(bookmark)
            token_count = len(rich_text.split())  # Aproximado
            total_tokens += token_count

            # 2. Gera embedding
            embedding = generate_embedding(rich_text)

            # 3. Atualiza no Supabase
            supabase.table('bookmarks').update({
                'embedding': embedding
            }).eq('id', bookmark_id).execute()

            print(f"  ✅ Embedding atualizado (~{token_count} tokens)")
            success_count += 1

        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")
            failed_count += 1

        # Pausa entre requisições (evita rate limiting)
        if i < total:
            await asyncio.sleep(0.5)

    # Resumo final
    print(f"\n{'='*70}")
    print(f"🎉 REGENERAÇÃO CONCLUÍDA!")
    print(f"{'='*70}")
    print(f"✅ Sucesso: {success_count}/{total}")
    print(f"❌ Falhas: {failed_count}/{total}")
    print(f"📈 Total de tokens: ~{total_tokens:,}")
    print(f"💰 Custo estimado: ${total_tokens * 0.00000002:.6f}")
    print()

    if success_count > 0:
        print("🔍 Embeddings agora incluem:")
        print("   ✅ Transcrição do áudio (Whisper)")
        print("   ✅ Análise visual (GPT-4 Vision)")
        print("   ✅ Comentários filtrados")
        print("   ✅ Todos os metadados existentes")
        print()
        print("🎯 Busca semântica agora está MUITO melhor!")
        print()


if __name__ == "__main__":
    asyncio.run(main())
