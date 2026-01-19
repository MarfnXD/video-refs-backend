#!/usr/bin/env python3
import os
from supabase import create_client

supabase_url = "https://twwpcnyqpwznzarguzit.supabase.co"
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

bookmark_id = "c3b11529-a446-429d-ad4c-a97fe072fbc5"

response = supabase.table('bookmarks').select(
    'id, url, cloud_video_url, title'
).eq('id', bookmark_id).execute()

if response.data:
    b = response.data[0]
    print(f"\n📌 BOOKMARK: {b['id'][:8]}...")
    print(f"\n🔗 URL ORIGINAL (Instagram):")
    print(f"   {b.get('url', 'N/A')}")
    print(f"\n☁️ URL DA CLOUD (Supabase Storage - enviada para Gemini):")
    cloud_url = b.get('cloud_video_url', 'N/A')
    print(f"   {cloud_url}")
    
    # Extrair path do vídeo
    if 'user-videos' in cloud_url:
        import re
        match = re.search(r'user-videos/([^?]+)', cloud_url)
        if match:
            video_path = match.group(1)
            print(f"\n📁 Path no storage: user-videos/{video_path}")
    
    print(f"\n📝 Título salvo: {b.get('title', 'N/A')}")
else:
    print("❌ Não encontrado")
