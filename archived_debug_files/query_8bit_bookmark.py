"""
Script para consultar bookmarks com "DPFquQ9D" no Supabase
"""
import os
import sys

# Carrega variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    print("❌ SUPABASE_KEY não encontrada")
    sys.exit(1)

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"\n{'='*80}")
print(f"🔍 BUSCANDO BOOKMARKS COM 'DPFquQ9D'")
print(f"{'='*80}\n")

# Busca bookmarks com URL contendo DPFquQ9D
response = supabase.table('bookmarks') \
    .select('*') \
    .ilike('url', '%DPFquQ9D%') \
    .order('created_at', desc=True) \
    .execute()

if not response.data:
    print("❌ Nenhum bookmark encontrado com 'DPFquQ9D' na URL")
    sys.exit(0)

print(f"✅ Encontrados {len(response.data)} bookmark(s):\n")

for i, bookmark in enumerate(response.data, 1):
    print(f"{'='*80}")
    print(f"BOOKMARK #{i}")
    print(f"{'='*80}")
    print(f"ID: {bookmark.get('id')}")
    print(f"Título: {bookmark.get('title')}")
    print(f"URL: {bookmark.get('url')}")
    print(f"Criado em: {bookmark.get('created_at')}")
    print(f"User ID: {bookmark.get('user_id')}")

    print(f"\n📊 STATUS DOS DADOS:")

    # Metadados básicos
    metadata = bookmark.get('metadata', {}) or {}
    print(f"   Metadata: {'✅ Sim' if metadata else '❌ Não'} ({len(metadata)} chaves)")
    if metadata:
        print(f"      - description: {'✅' if metadata.get('description') else '❌'}")
        print(f"      - hashtags: {'✅' if metadata.get('hashtags') else '❌'} ({len(metadata.get('hashtags', []))} tags)")
        print(f"      - top_comments: {'✅' if metadata.get('top_comments') else '❌'} ({len(metadata.get('top_comments', []))} comentários)")
        print(f"      - views: {metadata.get('views', 0)}")
        print(f"      - likes: {metadata.get('likes', 0)}")

    # Processamento IA
    auto_tags = bookmark.get('auto_tags') or []
    auto_categories = bookmark.get('auto_categories') or []
    filtered_comments = bookmark.get('filtered_comments') or []

    print(f"\n   IA Processada: {'✅' if bookmark.get('ai_processed') else '❌'}")
    print(f"      - auto_description: {'✅' if bookmark.get('auto_description') else '❌'}")
    print(f"      - auto_tags: {'✅' if auto_tags else '❌'} ({len(auto_tags)} tags)")
    print(f"      - auto_categories: {'✅' if auto_categories else '❌'} ({len(auto_categories)} cats)")
    print(f"      - relevance_score: {bookmark.get('relevance_score', 'N/A')}")

    # Análise multimodal
    print(f"\n   Análise Multimodal:")
    print(f"      - video_transcript: {'✅' if bookmark.get('video_transcript') else '❌'}")
    print(f"      - visual_analysis: {'✅' if bookmark.get('visual_analysis') else '❌'}")
    print(f"      - filtered_comments: {'✅' if filtered_comments else '❌'} ({len(filtered_comments)} comentários)")

    # Status de download/cloud
    print(f"\n   Vídeo:")
    print(f"      - local_video_path: {'✅' if bookmark.get('local_video_path') else '❌'}")
    print(f"      - cloud_video_url: {'✅' if bookmark.get('cloud_video_url') else '❌'}")

    print()

print(f"{'='*80}\n")
