#!/usr/bin/env python3
"""
Script para ZERAR COMPLETAMENTE o app Video Refs

⚠️ ATENÇÃO: Este script é DESTRUTIVO e IRREVERSÍVEL!

Deleta:
1. Todos os bookmarks do banco de dados
2. Todos os vídeos do Supabase Storage (user-videos)
3. Todas as thumbnails do Supabase Storage (thumbnails)

IMPORTANTE: Faça backup antes de executar!
"""

import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")

def confirm_deletion():
    """Pede confirmação tripla do usuário"""
    print("\n" + "="*80)
    print("⚠️  ATENÇÃO: OPERAÇÃO DESTRUTIVA E IRREVERSÍVEL!")
    print("="*80)
    print("\nEste script vai DELETAR PERMANENTEMENTE:")
    print("   ❌ TODOS os bookmarks do banco de dados")
    print("   ❌ TODOS os vídeos do Supabase Storage")
    print("   ❌ TODAS as thumbnails do Supabase Storage")
    print("\n⚠️  NÃO HÁ COMO DESFAZER ESTA OPERAÇÃO!")
    print("\nCertifique-se de que fez backup dos dados importantes!\n")

    # Confirmação 1
    resp1 = input("Você tem certeza ABSOLUTA que quer continuar? (digite 'SIM' em maiúsculas): ")
    if resp1 != "SIM":
        print("\n❌ Operação cancelada pelo usuário.")
        sys.exit(0)

    # Confirmação 2
    resp2 = input("\nDigite 'DELETE TUDO' para confirmar: ")
    if resp2 != "DELETE TUDO":
        print("\n❌ Operação cancelada pelo usuário.")
        sys.exit(0)

    # Confirmação 3 - última chance
    print("\n🚨 ÚLTIMA CHANCE! Esta é sua última oportunidade de cancelar.")
    resp3 = input("Digite 'CONFIRMO EXCLUSÃO TOTAL' para prosseguir: ")
    if resp3 != "CONFIRMO EXCLUSÃO TOTAL":
        print("\n❌ Operação cancelada pelo usuário.")
        sys.exit(0)

    print("\n✅ Confirmação recebida. Iniciando deleção em 3 segundos...")
    import time
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    print("")

def reset_app():
    """Reseta completamente o app"""

    print("🔌 Conectando ao Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # ========================================
    # 1. Estatísticas ANTES da deleção
    # ========================================
    print("\n📊 Coletando estatísticas atuais...")

    # Conta bookmarks
    response = supabase.table('bookmarks').select('id', count='exact').execute()
    total_bookmarks = response.count
    print(f"   📚 Bookmarks no banco: {total_bookmarks}")

    # Lista arquivos em user-videos
    try:
        videos_list = supabase.storage.from_('user-videos').list()
        total_videos = 0
        for item in videos_list:
            if item.get('name'):  # Conta arquivos, não pastas
                # Se for um diretório, lista recursivamente
                if item.get('id') is None:  # É uma pasta
                    folder_contents = supabase.storage.from_('user-videos').list(item['name'])
                    total_videos += len(folder_contents)
                else:
                    total_videos += 1
        print(f"   🎬 Vídeos no storage: {total_videos}")
    except Exception as e:
        print(f"   ⚠️  Erro ao contar vídeos: {e}")
        total_videos = 0

    # Lista arquivos em thumbnails
    try:
        thumbs_list = supabase.storage.from_('thumbnails').list()
        total_thumbs = len([t for t in thumbs_list if t.get('name')])
        print(f"   🖼️  Thumbnails no storage: {total_thumbs}")
    except Exception as e:
        print(f"   ⚠️  Erro ao contar thumbnails: {e}")
        total_thumbs = 0

    # ========================================
    # 2. DELETAR VÍDEOS do Storage
    # ========================================
    print("\n🗑️  DELETANDO vídeos do Supabase Storage...")
    videos_deleted = 0
    try:
        # Lista TODOS os arquivos recursivamente
        videos_list = supabase.storage.from_('user-videos').list()
        for item in videos_list:
            if item.get('id') is None:  # É uma pasta (user_id)
                user_folder = item['name']
                print(f"   📁 Deletando pasta: {user_folder}")
                # Lista arquivos dentro da pasta
                folder_contents = supabase.storage.from_('user-videos').list(user_folder)
                for video_file in folder_contents:
                    file_path = f"{user_folder}/{video_file['name']}"
                    try:
                        supabase.storage.from_('user-videos').remove([file_path])
                        videos_deleted += 1
                        print(f"      ✅ Deletado: {file_path}")
                    except Exception as e:
                        print(f"      ❌ Erro ao deletar {file_path}: {e}")

        print(f"\n   ✅ Total de vídeos deletados: {videos_deleted}")
    except Exception as e:
        print(f"   ❌ Erro ao deletar vídeos: {e}")

    # ========================================
    # 3. DELETAR THUMBNAILS do Storage
    # ========================================
    print("\n🗑️  DELETANDO thumbnails do Supabase Storage...")
    thumbs_deleted = 0
    try:
        thumbs_list = supabase.storage.from_('thumbnails').list()
        files_to_delete = [t['name'] for t in thumbs_list if t.get('name')]

        if files_to_delete:
            # Delete em lote (mais eficiente)
            supabase.storage.from_('thumbnails').remove(files_to_delete)
            thumbs_deleted = len(files_to_delete)
            print(f"   ✅ Total de thumbnails deletadas: {thumbs_deleted}")
        else:
            print("   ℹ️  Nenhuma thumbnail encontrada")
    except Exception as e:
        print(f"   ❌ Erro ao deletar thumbnails: {e}")

    # ========================================
    # 4. DELETAR BOOKMARKS do banco de dados
    # ========================================
    print("\n🗑️  DELETANDO bookmarks do banco de dados...")
    try:
        # Delete SEM filtro = deleta tudo
        result = supabase.table('bookmarks').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"   ✅ Total de bookmarks deletados: {total_bookmarks}")
    except Exception as e:
        print(f"   ❌ Erro ao deletar bookmarks: {e}")

    # ========================================
    # 5. VERIFICAÇÃO FINAL
    # ========================================
    print("\n🔍 Verificando se ficou algo...")

    # Verifica bookmarks
    response = supabase.table('bookmarks').select('id', count='exact').execute()
    remaining_bookmarks = response.count

    # Verifica storage
    try:
        videos_list = supabase.storage.from_('user-videos').list()
        remaining_videos = sum(1 for v in videos_list if v.get('name'))
    except:
        remaining_videos = 0

    try:
        thumbs_list = supabase.storage.from_('thumbnails').list()
        remaining_thumbs = sum(1 for t in thumbs_list if t.get('name'))
    except:
        remaining_thumbs = 0

    print(f"   📚 Bookmarks restantes: {remaining_bookmarks}")
    print(f"   🎬 Vídeos restantes: {remaining_videos}")
    print(f"   🖼️  Thumbnails restantes: {remaining_thumbs}")

    # ========================================
    # RESUMO FINAL
    # ========================================
    print("\n" + "="*80)
    print("✅ RESET COMPLETO FINALIZADO!")
    print("="*80)
    print("\n📊 RESUMO:")
    print(f"   Bookmarks deletados: {total_bookmarks} → {remaining_bookmarks}")
    print(f"   Vídeos deletados: {videos_deleted}")
    print(f"   Thumbnails deletadas: {thumbs_deleted}")

    if remaining_bookmarks == 0 and remaining_videos == 0 and remaining_thumbs == 0:
        print("\n🎉 App totalmente limpo! Pronto para começar do zero.")
    else:
        print("\n⚠️  Alguns itens não foram deletados. Verifique manualmente.")

if __name__ == "__main__":
    confirm_deletion()
    reset_app()
