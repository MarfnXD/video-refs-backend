"""
Script para regenerar TODOS os embeddings (incluindo os que já existem) com contexto semântico.

FORÇA a regeneração de todos os embeddings, independente se já existem ou não.
"""

import sys
from generate_embeddings import (
    supabase,
    create_rich_text,
    create_semantic_context,
    generate_embedding
)


def regenerate_all_embeddings():
    """
    Regenera embeddings de TODOS os bookmarks com contexto semântico melhorado.
    """
    print("\n🔄 REGENERANDO TODOS OS EMBEDDINGS COM CONTEXTO SEMÂNTICO")
    print("=" * 70)

    # Busca TODOS os bookmarks (não filtra por embedding null)
    print("📊 Buscando todos os bookmarks...")
    response = supabase.table("bookmarks").select("*").execute()
    bookmarks = response.data

    if not bookmarks:
        print("❌ Nenhum bookmark encontrado")
        return

    # Filtra apenas os que têm campos necessários para embedding
    bookmarks_with_content = [
        b for b in bookmarks
        if b.get('smart_title') or b.get('title') or b.get('auto_description')
    ]

    print(f"✅ {len(bookmarks_with_content)} bookmarks encontrados no banco")
    print()

    processed = 0
    failed = 0
    skipped = 0

    for i, bookmark in enumerate(bookmarks_with_content, 1):
        try:
            title = bookmark.get('smart_title') or bookmark.get('title') or 'Sem título'
            print(f"[{i}/{len(bookmarks_with_content)}] Processando: {title[:60]}...")

            # Mostra contexto semântico gerado (apenas primeiros 3)
            if i <= 3:
                semantic_context = create_semantic_context(bookmark)
                if semantic_context:
                    print(f"    💡 Contexto: {semantic_context[:100]}...")

            # Cria texto rico com novo contexto
            rich_text = create_rich_text(bookmark)

            # Mostra preview do texto (apenas primeiro bookmark)
            if i == 1:
                print("\n" + "-" * 70)
                print("📝 Preview do texto rico gerado (primeiro bookmark):")
                print("-" * 70)
                print(rich_text[:500] + "...")
                print("-" * 70)
                print()

            # Gera embedding
            embedding = generate_embedding(rich_text)

            if embedding:
                # Atualiza no Supabase (converte para JSON string)
                import json
                supabase.table("bookmarks").update({
                    "embedding": json.dumps(embedding)
                }).eq("id", bookmark['id']).execute()

                processed += 1
                print(f"    ✅ Embedding atualizado ({len(embedding)} dims)")
            else:
                failed += 1
                print(f"    ❌ Falha ao gerar embedding")

        except Exception as e:
            failed += 1
            print(f"    ❌ Erro: {e}")

        # Progress a cada 10
        if i % 10 == 0:
            print(f"\n📊 Progresso: {processed} processados, {failed} falhas\n")

    # Resumo
    print()
    print("=" * 70)
    print("✅ REGENERAÇÃO CONCLUÍDA!")
    print(f"📊 Processados: {processed}/{len(bookmarks_with_content)}")
    print(f"❌ Falhas: {failed}")
    print("=" * 70)


if __name__ == "__main__":
    # Confirmação de segurança
    print("\n⚠️  ATENÇÃO: Este script vai REGENERAR TODOS os embeddings!")
    print("Isso vai substituir embeddings existentes.")
    print()
    print("Deseja continuar? (y/n): ", end="")

    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("y (forçado via --force)")
        regenerate_all_embeddings()
    else:
        confirm = input()
        if confirm.lower() == 'y':
            regenerate_all_embeddings()
        else:
            print("❌ Cancelado pelo usuário")
