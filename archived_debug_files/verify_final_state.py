#!/usr/bin/env python3
"""Verificação final do estado do storage"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")

def check_bucket(bucket_name):
    print(f"\n{'='*60}")
    print(f"🔍 Bucket: {bucket_name}")
    print(f"{'='*60}")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    try:
        items = supabase.storage.from_(bucket_name).list()
        
        if not items:
            print("✅ Bucket VAZIO (nenhum item encontrado)")
            return True
        
        # Conta arquivos vs pastas
        files = [item for item in items if item.get('id') is not None]
        folders = [item for item in items if item.get('id') is None]
        
        print(f"📊 Total de itens: {len(items)}")
        print(f"   📁 Pastas: {len(folders)}")
        print(f"   📄 Arquivos na raiz: {len(files)}")
        
        # Verifica conteúdo de pastas
        total_files_in_folders = 0
        for folder in folders:
            folder_name = folder['name']
            folder_contents = supabase.storage.from_(bucket_name).list(folder_name)
            files_count = len([f for f in folder_contents if f.get('name')])
            total_files_in_folders += files_count
            
            if files_count > 0:
                print(f"   📁 {folder_name}/: {files_count} arquivos")
            else:
                print(f"   📁 {folder_name}/: VAZIA ✓")
        
        print(f"\n📈 RESUMO:")
        print(f"   Total de ARQUIVOS: {len(files) + total_files_in_folders}")
        
        if len(files) + total_files_in_folders == 0:
            print("\n🎉 Bucket LIMPO! (apenas pastas vazias do sistema)")
            return True
        else:
            print(f"\n⚠️  Ainda há {len(files) + total_files_in_folders} arquivos!")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

print("\n" + "="*60)
print("🔍 VERIFICAÇÃO FINAL DO ESTADO DO STORAGE")
print("="*60)

user_videos_clean = check_bucket('user-videos')
thumbnails_clean = check_bucket('thumbnails')

print("\n" + "="*60)
print("📊 RESULTADO FINAL")
print("="*60)
print(f"user-videos: {'✅ LIMPO' if user_videos_clean else '❌ COM ARQUIVOS'}")
print(f"thumbnails: {'✅ LIMPO' if thumbnails_clean else '❌ COM ARQUIVOS'}")

if user_videos_clean and thumbnails_clean:
    print("\n🎉🎉🎉 STORAGE COMPLETAMENTE LIMPO! 🎉🎉🎉")
else:
    print("\n⚠️  Storage ainda contém arquivos.")
