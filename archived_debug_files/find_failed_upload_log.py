"""
Buscar ID do vídeo que falhou upload para encontrar no log do Render
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Buscar o vídeo que completou sem cloud
result = supabase.table('bookmarks').select(
    'id, url, title, processing_status, cloud_video_url, created_at'
).eq('id', 'd49a39ec-2fc1-4ef0-b8ed-0ce2b5d497e9').execute()

if result.data:
    bm = result.data[0]
    print("="*80)
    print("VÍDEO QUE COMPLETOU SEM CLOUD")
    print("="*80)
    print(f"ID: {bm['id']}")
    print(f"Título: {bm['title'][:80]}")
    print(f"URL: {bm['url']}")
    print(f"Status: {bm['processing_status']}")
    print(f"Cloud URL: {bm.get('cloud_video_url', 'NÃO')}")
    print(f"Criado em: {bm['created_at']}")
    print()
    print("="*80)
    print("PROCURAR NO LOG DO RENDER:")
    print("="*80)
    print(f"Buscar por: {bm['id']}")
    print(f"Ou por: d49a39ec")
    print()
    print("Procurar erros relacionados a:")
    print("- RemoteProtocolError")
    print("- ReadTimeout")
    print("- ConnectTimeout")
    print("- Upload falhou")
    print("- httpx errors")
else:
    print("Bookmark não encontrado")
