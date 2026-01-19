"""
Verifica especificamente o bookmark do Red Bull x Arcane
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ID do bookmark Red Bull (do teste anterior)
bookmark_id = 'eefc288c-655a-4abb-b1c7-ac79460d3cf6'

print("=" * 80)
print(f"🔍 Verificando Red Bull x Arcane")
print("=" * 80)
print()

result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()

if not result.data:
    print("❌ Bookmark não encontrado!")
else:
    data = result.data

    print(f"Bookmark ID: {bookmark_id}")
    print(f"Smart Title: {data.get('smart_title')}")
    print()
    print(f"URL do vídeo: {data.get('url')}")
    print()
    
    # Thumbnails
    cloud_thumbnail_url = data.get('cloud_thumbnail_url')
    thumbnail_url = data.get('thumbnail_url')  # Instagram original
    
    print("THUMBNAILS:")
    print("-" * 80)
    
    if cloud_thumbnail_url:
        print(f"✅ cloud_thumbnail_url existe:")
        print(f"   {cloud_thumbnail_url}")
        print()
        
        # Verificar se é do Supabase ou Instagram
        if 'supabase' in cloud_thumbnail_url.lower():
            print("   ✅ Aponta para Supabase Storage")
        elif 'instagram' in cloud_thumbnail_url.lower() or 'cdninstagram' in cloud_thumbnail_url.lower():
            print("   ❌ ERRO: Aponta para Instagram em vez de Supabase!")
        else:
            print("   ⚠️  Não reconhecido")
    else:
        print(f"❌ cloud_thumbnail_url: NULL")
    
    print()
    
    if thumbnail_url:
        print(f"ℹ️  thumbnail_url (Instagram original):")
        print(f"   {thumbnail_url[:100]}...")
    else:
        print(f"ℹ️  thumbnail_url (Instagram): NULL")
    
    print()
    print("=" * 80)
    
    # Diagnóstico
    if not cloud_thumbnail_url:
        print("❌ PROBLEMA: Thumbnail não foi enviada para o Supabase")
        print("   Solução: Rodar fix_missing_thumbnails.py")
    elif 'instagram' in cloud_thumbnail_url.lower():
        print("❌ PROBLEMA: cloud_thumbnail_url aponta para Instagram")
        print("   Isso vai causar thumb quebrada no app!")
        print("   Solução: Reprocessar upload da thumbnail")
    else:
        print("✅ Thumbnail parece estar configurada corretamente")
        print()
        print("Se está aparecendo quebrada no app, pode ser:")
        print("  1. Signed URL expirada (gerar nova)")
        print("  2. Imagem corrompida no upload")
        print("  3. Permissões do Storage incorretas")
        print()
        print("Testar acessando a URL diretamente:")
        print(f"  {cloud_thumbnail_url}")
