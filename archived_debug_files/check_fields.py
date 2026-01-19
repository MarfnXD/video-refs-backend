#!/usr/bin/env python3
"""
Verifica se os 5 campos novos foram salvos no bookmark processado
"""
import os
from supabase import create_client

# Supabase client
supabase_url = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Bookmark ID do log do Render
bookmark_id = "f34ce850-e2a1-44f5-b20d-102e828cde64"

# Buscar bookmark
response = supabase.table('bookmarks').select(
    'id, title, original_title, thumbnail, cloud_thumbnail_url, '
    'published_at, user_context_raw, ai_processed, processing_status, '
    'auto_tags, auto_categories'
).eq('id', bookmark_id).execute()

if response.data:
    bookmark = response.data[0]
    print("\n✅ BOOKMARK ENCONTRADO NO BANCO:")
    print(f"ID: {bookmark['id']}")
    print(f"Status: {bookmark['processing_status']}")
    print("\n📊 CAMPOS NOVOS:")
    print(f"   title: {bookmark.get('title')}")
    print(f"   original_title: {bookmark.get('original_title')} {'✅' if bookmark.get('original_title') else '❌ FALTANDO!'}")
    print(f"   thumbnail: {bookmark.get('thumbnail')} {'✅' if bookmark.get('thumbnail') else '❌ FALTANDO!'}")
    print(f"   cloud_thumbnail_url: {bookmark.get('cloud_thumbnail_url')} {'✅' if bookmark.get('cloud_thumbnail_url') else '❌ FALTANDO!'}")
    print(f"   published_at: {bookmark.get('published_at')} {'✅' if bookmark.get('published_at') else '❌ FALTANDO!'}")
    print(f"   user_context_raw: {bookmark.get('user_context_raw')} {'✅' if bookmark.get('user_context_raw') else '⚠️ Nenhum (esperado se não adicionou contexto)'}")
    print(f"   ai_processed: {bookmark.get('ai_processed')} {'✅' if bookmark.get('ai_processed') else '❌ FALTANDO!'}")
    print("\n🤖 PROCESSAMENTO IA:")
    print(f"   auto_tags: {bookmark.get('auto_tags')}")
    print(f"   auto_categories: {bookmark.get('auto_categories')}")
else:
    print(f"❌ Bookmark {bookmark_id} NÃO encontrado!")
