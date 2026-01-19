#!/usr/bin/env python3
import os
from supabase import create_client

supabase_url = "https://twwpcnyqpwznzarguzit.supabase.co"
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

bookmark_id = "f34ce850-e2a1-44f5-b20d-102e828cde64"

# Buscar metadata completo
response = supabase.table('bookmarks').select('metadata').eq('id', bookmark_id).execute()

if response.data and response.data[0].get('metadata'):
    metadata = response.data[0]['metadata']
    print(f"\n🔍 METADATA JSON:")
    print(f"   cloud_thumbnail_url: {metadata.get('cloud_thumbnail_url')}")
    print(f"   thumbnail_url: {metadata.get('thumbnail_url')}")
    print(f"\n📋 Todos os campos no metadata:")
    for key in metadata.keys():
        print(f"   - {key}")
else:
    print("❌ Metadata não encontrado")
