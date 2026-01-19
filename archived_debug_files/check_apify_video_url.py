"""
Verificar se o bookmark d49a39ec tem video_url do Apify
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

result = supabase.table('bookmarks').select(
    'id, title, video_url, cloud_video_url, processing_status, thumbnail_url'
).eq('id', 'd49a39ec-2fc1-4ef0-b8ed-0ce2b5d497e9').execute()

if result.data:
    bm = result.data[0]
    print("="*80)
    print("DADOS DO BOOKMARK d49a39ec")
    print("="*80)
    print(f"Título: {bm['title'][:60]}")
    print(f"Status: {bm['processing_status']}")
    print()
    print(f"video_url (Apify): {'✅ SIM' if bm.get('video_url') else '❌ NÃO'}")
    if bm.get('video_url'):
        print(f"  {bm['video_url'][:80]}...")
    print()
    print(f"cloud_video_url (Supabase): {'✅ SIM' if bm.get('cloud_video_url') else '❌ NÃO'}")
    if bm.get('cloud_video_url'):
        print(f"  {bm['cloud_video_url'][:80]}...")
    print()
    print(f"thumbnail_url: {'✅ SIM' if bm.get('thumbnail_url') else '❌ NÃO'}")
    if bm.get('thumbnail_url'):
        print(f"  {bm['thumbnail_url'][:80]}...")
    print()
    print("="*80)
    print("DIAGNÓSTICO")
    print("="*80)
    
    if not bm.get('video_url'):
        print("❌ PROBLEMA: video_url do Apify está vazio!")
        print("   Causa: Apify não conseguiu extrair o vídeo")
        print("   Solução: URL do Instagram pode estar quebrada ou privada")
    elif bm.get('video_url') and not bm.get('cloud_video_url'):
        print("⚠️  PROBLEMA: video_url existe mas cloud_video_url não!")
        print("   Causa: Upload para Supabase falhou")
        print("   Solução: Reprocessar com retry automático")
    else:
        print("✅ Tudo OK")
else:
    print("Bookmark não encontrado")
