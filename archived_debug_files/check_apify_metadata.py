#!/usr/bin/env python3
import os
import json
from supabase import create_client

supabase_url = "https://twwpcnyqpwznzarguzit.supabase.co"
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

bookmark_id = "c3b11529-a446-429d-ad4c-a97fe072fbc5"

response = supabase.table('bookmarks').select('url, title, metadata').eq('id', bookmark_id).execute()

if response.data:
    b = response.data[0]
    print(f"\n🔗 URL: {b['url']}")
    print(f"📝 Título: {b['title']}")
    
    metadata = b.get('metadata')
    if metadata:
        print("\n" + "="*80)
        print("📥 METADADOS APIFY COMPLETOS:")
        print("="*80)
        print(json.dumps(metadata, indent=2, ensure_ascii=False)[:2000])
        print("\n...")
else:
    print("❌ Não encontrado")
