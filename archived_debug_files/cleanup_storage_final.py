#!/usr/bin/env python3
"""
Script para limpar completamente os buckets de storage
Remove TODOS os arquivos e pastas vazias
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")

def cleanup_bucket(bucket_name):
    """Limpa completamente um bucket"""
    print(f"\n🗑️  Limpando bucket: {bucket_name}")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    try:
        # Lista TUDO recursivamente
        all_files = supabase.storage.from_(bucket_name).list()

        # Primeiro: deleta arquivos dentro de pastas
        for item in all_files:
            if item.get('id') is None:  # É uma pasta
                folder_name = item['name']
                print(f"   📁 Limpando pasta: {folder_name}")

                # Lista conteúdo da pasta
                folder_contents = supabase.storage.from_(bucket_name).list(folder_name)

                # Prepara lista de paths completos
                files_to_delete = [f"{folder_name}/{f['name']}" for f in folder_contents if f.get('name')]

                if files_to_delete:
                    # Delete em lote
                    result = supabase.storage.from_(bucket_name).remove(files_to_delete)
                    print(f"      ✅ Deletados {len(files_to_delete)} arquivos")

        # Segundo: deleta arquivos soltos na raiz
        root_files = [f['name'] for f in all_files if f.get('id') is not None]
        if root_files:
            supabase.storage.from_(bucket_name).remove(root_files)
            print(f"   ✅ Deletados {len(root_files)} arquivos da raiz")

        # Verifica resultado final
        remaining = supabase.storage.from_(bucket_name).list()
        remaining_count = len([r for r in remaining if r.get('name')])

        print(f"   📊 Arquivos restantes: {remaining_count}")

        if remaining_count == 0:
            print(f"   🎉 Bucket {bucket_name} totalmente limpo!")
        else:
            print(f"   ⚠️  Ainda restam {remaining_count} itens:")
            for r in remaining:
                print(f"      - {r.get('name', 'unnamed')}")

    except Exception as e:
        print(f"   ❌ Erro ao limpar bucket {bucket_name}: {e}")

def main():
    print("="*80)
    print("🧹 LIMPEZA FINAL DOS BUCKETS DE STORAGE")
    print("="*80)

    # Limpa os 2 buckets
    cleanup_bucket('user-videos')
    cleanup_bucket('thumbnails')

    print("\n" + "="*80)
    print("✅ LIMPEZA FINALIZADA!")
    print("="*80)

if __name__ == "__main__":
    main()
