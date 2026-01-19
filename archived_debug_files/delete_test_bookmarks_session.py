"""
Deleta bookmarks de teste da sessão
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Bookmarks de teste criados nesta sessão
TEST_BOOKMARKS = [
    '65ffaa23-4d44-4216-aef7-bf6591282e4c',  # Teste pós-deploy (falhou - sem conteúdo)
    '887430ad-9355-4d65-9fa8-cd67ef6cf9e0',  # Teste single fix (travado - sem conteúdo)
    'afa22f9c-1da3-4126-ae78-97a40978b37d',  # Teste inicial (sem conteúdo)
    'eefc288c-655a-4abb-b1c7-ac79460d3cf6',  # Red Bull (reprocessado - sem thumb)
    '9d0a8bf8-3006-4c99-9b02-1b4b11cd1c5f',  # Teste migrate 5 (sem thumb)
    '88788190-2bf6-474c-9391-60bc63c6c8ec',  # Teste migrate 5
    'f49ad048-d3b8-4669-b3f8-113c66a382f5',  # Teste migrate 5
    'a040b835-1d19-4d7f-ae17-0d52a024e7ce',  # Teste migrate 5 (timeout)
]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🗑️  DELETANDO BOOKMARKS DE TESTE")
print("=" * 80)
print()

deleted = 0
not_found = 0
errors = 0

for bookmark_id in TEST_BOOKMARKS:
    try:
        # Verificar se existe
        result = supabase.table('bookmarks').select('id, smart_title, url').eq('id', bookmark_id).execute()

        if result.data:
            bm = result.data[0]
            print(f"Deletando: {bookmark_id[:8]}...")
            print(f"  Title: {bm.get('smart_title', 'N/A')[:50]}")
            print(f"  URL: {bm.get('url', 'N/A')[:50]}...")

            # Deletar
            supabase.table('bookmarks').delete().eq('id', bookmark_id).execute()
            print(f"  ✅ Deletado")
            deleted += 1
        else:
            print(f"⚠️  {bookmark_id[:8]}... não encontrado (já foi deletado?)")
            not_found += 1

        print()

    except Exception as e:
        print(f"❌ Erro ao deletar {bookmark_id[:8]}...: {str(e)}")
        errors += 1
        print()

print("=" * 80)
print("RESUMO:")
print("=" * 80)
print(f"✅ Deletados: {deleted}")
print(f"⚠️  Não encontrados: {not_found}")
print(f"❌ Erros: {errors}")
print()
print("=" * 80)
