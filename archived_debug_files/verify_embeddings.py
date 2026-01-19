"""
Verifica se os embeddings foram realmente salvos no Supabase e testa similaridade.
"""

import os
from supabase import create_client, Client
import google.generativeai as genai

# Configuração
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ ERRO: GEMINI_API_KEY não encontrada")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# IDs dos 14 vídeos selecionados
SELECTED_IDS = [
    '3c2edf52-ac96-493b-9dfa-d34f2cccd038',  # Paródia AI
    '138caefd-6b9f-4c15-a4af-21c112678d37',  # Live Portrait
    'ba5475fc-9b91-401c-900c-280465c9fe2c',  # Cinematic AI Transitions
    'df92d854-29ec-4b42-b44f-475b12ba9476',  # Krea AI
]

print("\n🔍 VERIFICANDO EMBEDDINGS NO BANCO DE DADOS")
print("=" * 70)

# Query de teste (mesmo do teste anterior)
query = "estou trabalhando em curso aonde vou ensinar tecnicas de como usar IA para cricao de videos"

print(f"\nQuery: '{query}'")
print()

# Gera embedding da query
print("📊 Gerando embedding da query...")
result = genai.embed_content(
    model="models/text-embedding-004",
    content=query,
    task_type="retrieval_query"
)
query_embedding = result['embedding']
print(f"✅ Embedding gerado ({len(query_embedding)} dims)")
print()

# Busca os 4 primeiros vídeos selecionados
print("📦 Buscando vídeos no Supabase...")
response = supabase.table("bookmarks").select("*").in_("id", SELECTED_IDS).execute()
bookmarks = response.data

print(f"✅ {len(bookmarks)} bookmarks encontrados")
print()

# Verifica embeddings e calcula similaridade
print("=" * 70)
print("ANÁLISE DETALHADA:")
print("=" * 70)
print()

for bookmark in bookmarks:
    title = bookmark.get('smart_title') or bookmark.get('title') or 'Sem título'
    print(f"📹 {title[:60]}...")
    print(f"   ID: {bookmark['id']}")

    # Verifica se tem embedding
    has_embedding = bookmark.get('embedding') is not None
    print(f"   Embedding: {'✅ SIM' if has_embedding else '❌ NÃO'}")

    if has_embedding:
        video_emb = bookmark['embedding']

        # Mostra tipo e tamanho
        print(f"   Tipo: {type(video_emb)}")
        print(f"   Tamanho: {len(video_emb) if isinstance(video_emb, list) else 'N/A'}")

        # Calcula similaridade
        if isinstance(video_emb, list) and len(video_emb) == len(query_embedding):
            # Produto escalar
            dot_product = sum(a * b for a, b in zip(query_embedding, video_emb))

            # Normas
            norm_query = sum(a * a for a in query_embedding) ** 0.5
            norm_video = sum(b * b for b in video_emb) ** 0.5

            # Similaridade
            similarity = dot_product / (norm_query * norm_video)
            similarity_pct = similarity * 100

            print(f"   Similaridade: {similarity_pct:.1f}%")

            # Mostra primeiros 5 valores do embedding
            print(f"   Primeiros 5 valores: {video_emb[:5]}")
        else:
            print(f"   ⚠️ Tamanho incompatível ou tipo errado!")

    print()

# Agora busca TODOS os embeddings e mostra estatísticas
print("=" * 70)
print("ESTATÍSTICAS GERAIS:")
print("=" * 70)
print()

all_response = supabase.table("bookmarks").select("id, smart_title, title, embedding").execute()
all_bookmarks = all_response.data

total = len(all_bookmarks)
with_embedding = sum(1 for b in all_bookmarks if b.get('embedding'))
without_embedding = total - with_embedding

print(f"Total de bookmarks: {total}")
print(f"Com embedding: {with_embedding}")
print(f"Sem embedding: {without_embedding}")
print()

# Calcula similaridade de TODOS
print("📊 Calculando similaridade de TODOS os vídeos com a query...")
print()

similarities = []
for bookmark in all_bookmarks:
    if not bookmark.get('embedding'):
        continue

    video_emb = bookmark['embedding']

    if isinstance(video_emb, list) and len(video_emb) == len(query_embedding):
        dot_product = sum(a * b for a, b in zip(query_embedding, video_emb))
        norm_query = sum(a * a for a in query_embedding) ** 0.5
        norm_video = sum(b * b for b in video_emb) ** 0.5
        similarity = dot_product / (norm_query * norm_video)

        similarities.append({
            'id': bookmark['id'],
            'title': bookmark.get('smart_title') or bookmark.get('title'),
            'similarity': similarity * 100
        })

# Ordena por similaridade
similarities.sort(key=lambda x: x['similarity'], reverse=True)

print("🏆 TOP 10 VÍDEOS MAIS SIMILARES:")
print("-" * 70)
for i, item in enumerate(similarities[:10], 1):
    print(f"{i}. {item['similarity']:.1f}% - {item['title'][:55]}")

print()
print(f"📊 Range completo: {similarities[0]['similarity']:.1f}% - {similarities[-1]['similarity']:.1f}%")
print(f"📊 Média: {sum(s['similarity'] for s in similarities) / len(similarities):.1f}%")

# Verifica quantos dos 14 selecionados estão no top
print()
print("=" * 70)
print("VERIFICAÇÃO DOS 14 VÍDEOS SELECIONADOS:")
print("=" * 70)
print()

selected_in_top = [s for s in similarities if s['id'] in SELECTED_IDS]
selected_in_top.sort(key=lambda x: x['similarity'], reverse=True)

for item in selected_in_top:
    print(f"{item['similarity']:.1f}% - {item['title']}")

print()
print(f"✅ {len(selected_in_top)}/{len(SELECTED_IDS)} vídeos selecionados encontrados com embedding")
