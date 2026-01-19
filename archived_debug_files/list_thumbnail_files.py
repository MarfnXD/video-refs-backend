#!/usr/bin/env python3
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print("🔍 Listando conteúdo da pasta no bucket thumbnails...")
folder_contents = supabase.storage.from_('thumbnails').list('0ed9bb40-0041-4dca-9649-256cb418f403')

for item in folder_contents:
    print(f"   {item}")
    
print(f"\n📊 Total: {len(folder_contents)} arquivos")

# Tenta deletar diretamente
if folder_contents:
    print("\n🗑️  Deletando arquivo específico...")
    file_path = f"0ed9bb40-0041-4dca-9649-256cb418f403/{folder_contents[0]['name']}"
    try:
        result = supabase.storage.from_('thumbnails').remove([file_path])
        print(f"✅ Deletado: {file_path}")
    except Exception as e:
        print(f"❌ Erro: {e}")
