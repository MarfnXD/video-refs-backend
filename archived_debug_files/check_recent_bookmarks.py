#!/usr/bin/env python3
import os
from supabase import create_client

supabase_url = "https://twwpcnyqpwznzarguzit.supabase.co"
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Buscar últimos 5 bookmarks
response = supabase.table('bookmarks').select(
    'id, title, url, created_at, processing_status'
).order('created_at', desc=True).limit(5).execute()

if response.data:
    print("\n📋 ÚLTIMOS 5 BOOKMARKS:")
    print("="*80)
    for i, b in enumerate(response.data, 1):
        print(f"\n{i}. ID: {b['id'][:8]}...")
        print(f"   URL: {b.get('url', 'N/A')}")
        print(f"   Título: {b.get('title', 'N/A')[:80]}")
        print(f"   Status: {b.get('processing_status', 'N/A')}")
        print(f"   Criado: {b.get('created_at', 'N/A')}")
    print("\n" + "="*80)
else:
    print("❌ Nenhum bookmark encontrado")
