#!/usr/bin/env python3
"""
Verifica se TODOS os 5 campos essenciais foram salvos corretamente
"""
import os
from supabase import create_client

supabase_url = "https://twwpcnyqpwznzarguzit.supabase.co"
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Bookmark ID do último vídeo processado
bookmark_id = "73029d21-c420-4868-8c96-30332e7de919"

# Buscar bookmark
response = supabase.table('bookmarks').select(
    'id, title, original_title, thumbnail, cloud_thumbnail_url, '
    'published_at, user_context_raw, ai_processed, processing_status, '
    'auto_tags, auto_categories'
).eq('id', bookmark_id).execute()

print("\n" + "="*70)
print("🔍 VERIFICAÇÃO COMPLETA - TODOS OS CAMPOS ESSENCIAIS")
print("="*70)

if response.data:
    bookmark = response.data[0]
    print(f"\n✅ BOOKMARK ENCONTRADO: {bookmark['id'][:8]}...")
    print(f"📊 Status: {bookmark['processing_status']}")

    print("\n" + "-"*70)
    print("📋 CAMPOS ESSENCIAIS QUE ADICIONAMOS:")
    print("-"*70)

    # 1. original_title
    original_title = bookmark.get('original_title')
    print(f"\n1️⃣  original_title:")
    if original_title:
        print(f"    ✅ SALVO: {original_title[:60]}...")
    else:
        print(f"    ❌ FALTANDO!")

    # 2. thumbnail
    thumbnail = bookmark.get('thumbnail')
    print(f"\n2️⃣  thumbnail:")
    if thumbnail:
        print(f"    ✅ SALVO: {thumbnail[:80]}...")
    else:
        print(f"    ❌ FALTANDO!")

    # 3. cloud_thumbnail_url (O QUE ACABAMOS DE CORRIGIR)
    cloud_thumbnail_url = bookmark.get('cloud_thumbnail_url')
    print(f"\n3️⃣  cloud_thumbnail_url (CORRIGIDO):")
    if cloud_thumbnail_url:
        print(f"    ✅ SALVO: {cloud_thumbnail_url[:80]}...")
    else:
        print(f"    ❌ FALTANDO!")

    # 4. published_at
    published_at = bookmark.get('published_at')
    print(f"\n4️⃣  published_at:")
    if published_at:
        print(f"    ✅ SALVO: {published_at}")
    else:
        print(f"    ❌ FALTANDO!")

    # 5. user_context_raw
    user_context_raw = bookmark.get('user_context_raw')
    print(f"\n5️⃣  user_context_raw:")
    if user_context_raw:
        print(f"    ✅ SALVO: {user_context_raw[:60]}...")
    else:
        print(f"    ⚠️  None (esperado se não adicionou contexto)")

    # 6. ai_processed
    ai_processed = bookmark.get('ai_processed')
    print(f"\n6️⃣  ai_processed:")
    if ai_processed:
        print(f"    ✅ SALVO: True")
    else:
        print(f"    ❌ FALTANDO!")

    print("\n" + "-"*70)
    print("🤖 PROCESSAMENTO IA:")
    print("-"*70)
    print(f"   auto_tags: {bookmark.get('auto_tags')}")
    print(f"   auto_categories: {bookmark.get('auto_categories')}")

    print("\n" + "="*70)

    # Verificar se TODOS os campos estão OK
    all_ok = all([
        original_title,
        thumbnail,
        cloud_thumbnail_url,  # O mais importante!
        published_at,
        ai_processed
    ])

    if all_ok:
        print("✅ SUCESSO TOTAL! TODOS OS 5 CAMPOS SALVOS CORRETAMENTE!")
    else:
        print("⚠️  ATENÇÃO: Alguns campos ainda estão faltando")

    print("="*70 + "\n")
else:
    print(f"❌ Bookmark {bookmark_id} NÃO encontrado!")
