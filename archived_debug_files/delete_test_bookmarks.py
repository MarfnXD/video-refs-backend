#!/usr/bin/env python3
"""
Deleta os últimos 5 bookmarks de teste para reprocessar com pipeline corrigido
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🗑️  Deletando 5 bookmarks de teste...\n")

# Buscar últimos 5 bookmarks
result = supabase.table('bookmarks').select('id, url, created_at').order('created_at', desc=True).limit(5).execute()

if not result.data or len(result.data) == 0:
    print("❌ Nenhum bookmark encontrado")
    exit(0)

bookmarks = result.data
print(f"📋 Encontrados {len(bookmarks)} bookmarks:\n")

for idx, bookmark in enumerate(bookmarks, 1):
    print(f"{idx}. {bookmark['id'][:8]}... - {bookmark['url'][:60]}...")

print(f"\n🗑️  Deletando...")

for bookmark in bookmarks:
    bookmark_id = bookmark['id']

    # Deletar bookmark
    supabase.table('bookmarks').delete().eq('id', bookmark_id).execute()
    print(f"   ✓ Deletado: {bookmark_id[:8]}...")

print(f"\n✅ {len(bookmarks)} bookmarks deletados com sucesso!")
print("🎯 Pronto para reprocessar com pipeline corrigido\n")
