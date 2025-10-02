"""
Serviço de chat com IA para busca semântica de bookmarks.

Usa embeddings + busca vetorial + Claude API para conversação inteligente.
"""

from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
import os
import replicate

# Configuração
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# Clientes globais (carrega uma vez)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN) if REPLICATE_API_TOKEN else None


def generate_embedding(text: str) -> List[float]:
    """Gera embedding para um texto usando sentence-transformers."""
    return embedding_model.encode(text, convert_to_numpy=True).tolist()


def search_bookmarks(query: str, limit: int = 10, threshold: float = 0.3) -> List[Dict[str, Any]]:
    """
    Busca bookmarks semanticamente similares à query.

    Args:
        query: Texto da busca (pergunta do usuário)
        limit: Quantos resultados retornar
        threshold: Limiar de similaridade (0-1)

    Returns:
        Lista de bookmarks com similarity score
    """
    # Gera embedding da query
    query_embedding = generate_embedding(query)

    # Busca no Supabase usando função SQL
    response = supabase.rpc(
        'search_bookmarks_semantic',
        {
            'query_embedding': query_embedding,
            'match_threshold': threshold,
            'match_count': limit
        }
    ).execute()

    # Retorna resultados
    return response.data if response.data else []


def get_full_bookmark_data(bookmark_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Busca dados completos dos bookmarks (incluindo tags, categorias, etc).

    Args:
        bookmark_ids: Lista de IDs dos bookmarks

    Returns:
        Lista de bookmarks com todos os campos
    """
    if not bookmark_ids:
        return []

    response = supabase.table('bookmarks').select('*').in_('id', bookmark_ids).execute()
    return response.data if response.data else []


def format_bookmark_for_llm(bookmark: Dict[str, Any]) -> str:
    """
    Formata bookmark para enviar à IA (texto compacto e rico).
    """
    parts = []

    # Título
    parts.append(f"**{bookmark.get('title', 'Sem título')}**")

    # URL
    parts.append(f"URL: {bookmark.get('url', 'N/A')}")

    # Contexto do usuário (por que salvou)
    if bookmark.get('user_context_processed'):
        parts.append(f"Motivo: {bookmark['user_context_processed']}")

    # Descrição
    if bookmark.get('auto_description'):
        parts.append(f"Descrição: {bookmark['auto_description']}")

    # Tags
    all_tags = []
    if bookmark.get('tags'):
        all_tags.extend(bookmark['tags'])
    if bookmark.get('auto_tags'):
        all_tags.extend(bookmark['auto_tags'])
    if all_tags:
        parts.append(f"Tags: {', '.join(set(all_tags))}")

    # Categorias
    all_categories = []
    if bookmark.get('categories'):
        all_categories.extend(bookmark['categories'])
    if bookmark.get('auto_categories'):
        all_categories.extend(bookmark['auto_categories'])
    if all_categories:
        parts.append(f"Categorias: {', '.join(set(all_categories))}")

    return "\n".join(parts)


def chat_with_ai(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    max_bookmarks: int = 10
) -> Dict[str, Any]:
    """
    Processa mensagem do usuário e retorna resposta com bookmarks relevantes.

    Args:
        user_message: Mensagem/pergunta do usuário
        conversation_history: Histórico da conversa (opcional)
        max_bookmarks: Máximo de bookmarks para buscar

    Returns:
        {
            "message": "Resposta da IA",
            "bookmarks": [lista de bookmarks relevantes com IDs],
            "total_found": número total de resultados
        }
    """

    # 1. Busca semântica
    print(f"🔍 Buscando bookmarks para: '{user_message}'")
    search_results = search_bookmarks(user_message, limit=max_bookmarks, threshold=0.3)

    if not search_results:
        return {
            "message": "Não encontrei bookmarks relevantes para sua busca. Tente reformular a pergunta ou usar termos diferentes.",
            "bookmarks": [],
            "total_found": 0
        }

    print(f"✅ Encontrados: {len(search_results)} bookmarks")

    # 2. Busca dados completos
    bookmark_ids = [r['id'] for r in search_results]
    full_bookmarks = get_full_bookmark_data(bookmark_ids)

    # Ordena pelos IDs originais (mantém ordem de relevância)
    id_to_bookmark = {b['id']: b for b in full_bookmarks}
    sorted_bookmarks = [id_to_bookmark[bid] for bid in bookmark_ids if bid in id_to_bookmark]

    # 3. Prepara contexto para IA
    bookmarks_context = "\n\n---\n\n".join([
        format_bookmark_for_llm(b) for b in sorted_bookmarks[:5]  # Envia top 5 para IA
    ])

    # 4. Monta prompt para Claude
    system_prompt = """Você é um assistente especializado em ajudar profissionais criativos a encontrar referências visuais em sua biblioteca de vídeos salvos.

Sua função é:
1. Analisar a pergunta do usuário
2. Examinar os bookmarks encontrados pela busca semântica
3. Recomendar os mais relevantes de forma conversacional
4. Explicar POR QUÊ cada bookmark é relevante para a pergunta
5. Sugerir conexões criativas entre os bookmarks

Seja conciso, direto e útil. Foque no valor criativo."""

    user_prompt = f"""Pergunta do usuário: "{user_message}"

Bookmarks encontrados (já ordenados por relevância):

{bookmarks_context}

Analise esses bookmarks e responda ao usuário de forma conversacional, destacando os mais relevantes e explicando por que são úteis para a pergunta dele."""

    # 5. Chama Claude via Replicate
    if replicate_client:
        try:
            # Monta prompt final combinando system + user
            final_prompt = f"{system_prompt}\n\n{user_prompt}"

            # Chama Claude via Replicate
            output = replicate_client.run(
                "anthropic/claude-3.5-sonnet",
                input={
                    "prompt": final_prompt,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                }
            )

            # Concatena output (Replicate retorna generator)
            ai_message = "".join(output)

        except Exception as e:
            print(f"❌ Erro ao chamar Claude via Replicate: {e}")
            ai_message = f"Encontrei {len(sorted_bookmarks)} bookmarks relevantes para sua busca. Veja os resultados abaixo."
    else:
        # Fallback se não tiver Replicate configurado
        ai_message = f"Encontrei {len(sorted_bookmarks)} bookmarks relevantes. Aqui estão os top {min(5, len(sorted_bookmarks))} mais similares à sua busca."

    # 6. Retorna resposta
    return {
        "message": ai_message,
        "bookmarks": sorted_bookmarks,  # Retorna TODOS encontrados (UI pode paginar)
        "total_found": len(sorted_bookmarks)
    }
