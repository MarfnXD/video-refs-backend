"""
Script para regenerar embeddings de vídeos específicos usando o novo contexto semântico.

Regenera embeddings dos 14 vídeos selecionados manualmente com o novo create_semantic_context().
"""

import os
import sys

# Importa as funções do generate_embeddings.py
from generate_embeddings import (
    supabase,
    create_rich_text,
    create_semantic_context,
    generate_embedding
)

# IDs dos 14 vídeos selecionados manualmente
SELECTED_IDS = [
    '3c2edf52-ac96-493b-9dfa-d34f2cccd038',  # Paródia AI
    '138caefd-6b9f-4c15-a4af-21c112678d37',  # Live Portrait
    'ba5475fc-9b91-401c-900c-280465c9fe2c',  # Cinematic AI Transitions
    'df92d854-29ec-4b42-b44f-475b12ba9476',  # Krea AI
    '666dd8f4-6e6f-4674-bce4-0b7cd1585ab8',  # Power Rangers
    '79a9b4aa-9525-406b-8bdc-d2cd131538f1',  # Workflow VFX AI
    '12ad0bf5-9989-4c7f-98e6-79de44c20a67',  # Google Veo 2
    'bac0b6cf-8d0c-4870-822a-f346ffb656fd',  # Upscaling AI
    '0f5e3b86-566e-4d0a-bfcb-e6c9a91ae097',  # Tutorial Produto AI
    'edbe84e0-d85e-4c84-b9a0-75fdd441b883',  # Christmas 2250
    '51bf93c0-1dd6-46a7-8532-215072a846cd',  # Saitama vs Genos
    '0b8dece0-1c7c-41ce-9b08-214e6902d13c',  # InVideo AI
    '0223b7a0-8f46-4f16-b365-a7bbd5d6929d',  # App Instories
    'cf21bb4e-73d9-4d2b-a29f-e4d56910a7a6'   # Design Thumbnails
]


def regenerate_embeddings_for_selected():
    """
    Regenera embeddings dos 14 vídeos selecionados com contexto semântico melhorado.
    """
    print("\n🔄 REGENERANDO EMBEDDINGS COM CONTEXTO SEMÂNTICO MELHORADO")
    print("=" * 70)
    print(f"📦 {len(SELECTED_IDS)} vídeos selecionados")
    print()

    # Busca os bookmarks
    response = supabase.table("bookmarks").select("*").in_("id", SELECTED_IDS).execute()
    bookmarks = response.data

    if not bookmarks:
        print("❌ Nenhum bookmark encontrado com os IDs fornecidos")
        return

    print(f"✅ {len(bookmarks)} bookmarks encontrados no banco")
    print()

    processed = 0
    failed = 0

    for i, bookmark in enumerate(bookmarks, 1):
        try:
            title = bookmark.get('smart_title') or bookmark.get('title') or 'Sem título'
            print(f"[{i}/{len(bookmarks)}] Processando: {title[:60]}...")

            # Mostra contexto semântico gerado (debug)
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
                # Atualiza no Supabase
                supabase.table("bookmarks").update({
                    "embedding": embedding
                }).eq("id", bookmark['id']).execute()

                processed += 1
                print(f"    ✅ Embedding atualizado ({len(embedding)} dims)")
            else:
                failed += 1
                print(f"    ❌ Falha ao gerar embedding")

        except Exception as e:
            failed += 1
            print(f"    ❌ Erro: {e}")

        print()

    # Resumo
    print("=" * 70)
    print("✅ REGENERAÇÃO CONCLUÍDA!")
    print(f"📊 Processados: {processed}/{len(bookmarks)}")
    print(f"❌ Falhas: {failed}")
    print("=" * 70)


def test_improved_search():
    """
    Testa a busca com os embeddings melhorados.
    """
    print("\n🔍 TESTANDO BUSCA COM EMBEDDINGS MELHORADOS")
    print("=" * 70)
    print()

    query = "estou trabalhando em curso aonde vou ensinar tecnicas de como usar IA para cricao de videos"
    print(f"Query: '{query}'")
    print()

    # Gera embedding da query
    query_embedding = generate_embedding(query)

    if not query_embedding:
        print("❌ Erro ao gerar embedding da query")
        return

    # Busca apenas nos 14 vídeos selecionados
    print("Buscando similaridade nos 14 vídeos selecionados...")
    print()

    response = supabase.table("bookmarks").select("*").in_("id", SELECTED_IDS).execute()
    bookmarks = response.data

    # Calcula similaridade
    results = []
    for bookmark in bookmarks:
        if not bookmark.get('embedding'):
            continue

        # Calcula cosine similarity
        video_emb = bookmark['embedding']
        if isinstance(video_emb, str):
            import json
            video_emb = json.loads(video_emb)

        # Produto escalar
        dot_product = sum(a * b for a, b in zip(query_embedding, video_emb))

        # Normas
        norm_query = sum(a * a for a in query_embedding) ** 0.5
        norm_video = sum(b * b for b in video_emb) ** 0.5

        # Similaridade
        similarity = dot_product / (norm_query * norm_video)

        results.append({
            'title': bookmark.get('smart_title') or bookmark.get('title'),
            'similarity': similarity,
            'tags': bookmark.get('auto_tags', [])[:5]
        })

    # Ordena por similaridade
    results.sort(key=lambda x: x['similarity'], reverse=True)

    print("📊 RESULTADOS (ordenados por similaridade):")
    print("-" * 70)
    for i, result in enumerate(results, 1):
        sim_pct = result['similarity'] * 100
        status = "✅" if sim_pct >= 57 else "❌"
        print(f"{i}. {status} {sim_pct:.1f}% - {result['title']}")
        if result['tags']:
            print(f"      Tags: {', '.join(result['tags'])}")

    print()
    print("-" * 70)

    # Estatísticas
    above_threshold = sum(1 for r in results if r['similarity'] >= 0.57)
    avg_similarity = sum(r['similarity'] for r in results) / len(results)

    print()
    print(f"Vídeos acima de 57%: {above_threshold}/{len(results)}")
    print(f"Similaridade média: {avg_similarity * 100:.1f}%")
    print(f"Range: {results[0]['similarity'] * 100:.1f}% - {results[-1]['similarity'] * 100:.1f}%")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Modo teste: apenas verifica similaridade sem regenerar
        test_improved_search()
    else:
        # Regenera embeddings
        regenerate_embeddings_for_selected()

        # Pergunta se quer testar
        print("\n💡 Deseja testar a busca com os novos embeddings? (y/n): ", end="")
        if input().lower() == 'y':
            test_improved_search()
