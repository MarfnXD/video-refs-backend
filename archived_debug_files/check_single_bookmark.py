"""Verificar um bookmark específico"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

bookmark_id = '71ae7c74-8617-44fd-ba03-92ef3fe869b3'

result = supabase.table('bookmarks') \
    .select('id, processing_status, cloud_thumbnail_url, thumbnail, error_message') \
    .eq('id', bookmark_id) \
    .execute()

if result.data:
    bm = result.data[0]
    status = bm['processing_status']
    cloud_thumb = bm.get('cloud_thumbnail_url')
    thumb = bm.get('thumbnail')
    error = bm.get('error_message')

    print()
    print("=" * 80)
    print("📊 RESULTADO DO TESTE")
    print("=" * 80)
    print()
    print(f"Bookmark ID: {bookmark_id}")
    print(f"Status: {status}")
    print()

    if error:
        print(f"❌ ERRO: {error}")
        print()

    if thumb:
        print(f"Thumbnail original:")
        print(f"  {thumb[:100]}...")
        print()

    if cloud_thumb:
        is_supabase = 'supabase.co' in cloud_thumb
        is_instagram = 'instagram.com' in cloud_thumb or 'cdninstagram.com' in cloud_thumb

        print(f"Cloud Thumbnail:")
        print(f"  {cloud_thumb[:100]}...")
        print()

        if is_supabase:
            print("🎉 🎉 🎉 SUCESSO! Thumbnail salva no Supabase Storage!")
            print()
            print("✅ O upload de thumbnails está funcionando PERFEITAMENTE!")
        elif is_instagram:
            print("❌ ❌ ❌ FALHA! Thumbnail aponta para Instagram CDN!")
    else:
        print("⚠️  Cloud Thumbnail: N/A")
        if status == 'processing':
            print("⏳ Ainda processando... aguarde mais um pouco")
