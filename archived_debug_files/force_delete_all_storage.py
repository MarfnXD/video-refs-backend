#!/usr/bin/env python3
"""
Script FORÇADO para deletar TUDO dos buckets
Usa método mais agressivo
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")

def force_delete_bucket(bucket_name):
    """Deleta TUDO de um bucket usando método agressivo"""
    print(f"\n🔥 FORÇA BRUTA no bucket: {bucket_name}")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    try:
        # MÉTODO 1: Lista e deleta TUDO recursivamente
        print("   Método 1: Listando todos os arquivos...")
        all_items = supabase.storage.from_(bucket_name).list()

        # Coleta TODOS os paths
        paths_to_delete = []

        for item in all_items:
            item_name = item.get('name')
            if not item_name:
                continue

            # Se for pasta, lista conteúdo
            if item.get('id') is None:
                print(f"      📁 Explorando pasta: {item_name}")
                try:
                    folder_contents = supabase.storage.from_(bucket_name).list(item_name)
                    for file in folder_contents:
                        if file.get('name'):
                            full_path = f"{item_name}/{file['name']}"
                            paths_to_delete.append(full_path)
                            print(f"         + {full_path}")
                except Exception as e:
                    print(f"         ❌ Erro ao listar {item_name}: {e}")

                # Tenta deletar a pasta vazia depois
                paths_to_delete.append(item_name)
            else:
                # É arquivo na raiz
                paths_to_delete.append(item_name)

        print(f"\n   📊 Total de paths para deletar: {len(paths_to_delete)}")

        # Deleta em lotes de 100 (limite da API)
        batch_size = 100
        total_deleted = 0

        for i in range(0, len(paths_to_delete), batch_size):
            batch = paths_to_delete[i:i+batch_size]
            try:
                result = supabase.storage.from_(bucket_name).remove(batch)
                total_deleted += len(batch)
                print(f"   ✅ Lote {i//batch_size + 1}: {len(batch)} itens deletados")
            except Exception as e:
                print(f"   ❌ Erro no lote {i//batch_size + 1}: {e}")
                # Tenta deletar um por um
                for path in batch:
                    try:
                        supabase.storage.from_(bucket_name).remove([path])
                        total_deleted += 1
                        print(f"      ✅ {path}")
                    except Exception as e2:
                        print(f"      ❌ {path}: {e2}")

        print(f"\n   ✅ Total deletado: {total_deleted}/{len(paths_to_delete)}")

        # Verifica resultado final
        print("\n   🔍 Verificando o que sobrou...")
        remaining = supabase.storage.from_(bucket_name).list()
        remaining_count = 0
        for r in remaining:
            if r.get('name'):
                remaining_count += 1
                print(f"      ⚠️  Sobrou: {r.get('name')}")

                # Se for pasta vazia, tenta deletar manualmente
                if r.get('id') is None:
                    print(f"         Tentando deletar pasta vazia...")
                    try:
                        supabase.storage.from_(bucket_name).remove([r['name']])
                        print(f"         ✅ Pasta deletada!")
                    except Exception as e:
                        print(f"         ❌ Falhou: {e}")

        if remaining_count == 0:
            print(f"\n   🎉 Bucket {bucket_name} COMPLETAMENTE LIMPO!")
        else:
            print(f"\n   ⚠️  Ainda restam {remaining_count} itens (podem ser pastas vazias do sistema)")

    except Exception as e:
        print(f"   ❌ Erro geral: {e}")

def main():
    print("="*80)
    print("🔥 DELEÇÃO FORÇADA DE TODOS OS ARQUIVOS DOS BUCKETS")
    print("="*80)

    force_delete_bucket('user-videos')
    force_delete_bucket('thumbnails')

    print("\n" + "="*80)
    print("✅ PROCESSO FINALIZADO!")
    print("="*80)

if __name__ == "__main__":
    main()
