#!/usr/bin/env python3
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print("🔍 Verificando pasta aninhada...")
try:
    nested_contents = supabase.storage.from_('thumbnails').list('0ed9bb40-0041-4dca-9649-256cb418f403/thumbnails')
    print(f"📁 Conteúdo de 0ed9bb40-0041-4dca-9649-256cb418f403/thumbnails/:")
    for item in nested_contents:
        print(f"   {item}")
    print(f"\n📊 Total: {len(nested_contents)} arquivos")
    
    # Deleta arquivos dentro da subpasta
    if nested_contents:
        print("\n🗑️  Deletando arquivos da subpasta...")
        paths = [f"0ed9bb40-0041-4dca-9649-256cb418f403/thumbnails/{f['name']}" for f in nested_contents if f.get('name')]
        if paths:
            result = supabase.storage.from_('thumbnails').remove(paths)
            print(f"✅ Deletados {len(paths)} arquivos")
            
    # Deleta a subpasta vazia
    print("\n🗑️  Deletando subpasta vazia...")
    supabase.storage.from_('thumbnails').remove(['0ed9bb40-0041-4dca-9649-256cb418f403/thumbnails'])
    print("✅ Subpasta deletada")
    
except Exception as e:
    print(f"❌ Erro: {e}")
