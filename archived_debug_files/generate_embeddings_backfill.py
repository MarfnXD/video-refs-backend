#!/usr/bin/env python3
"""
SCRIPT DE BACKFILL - Gerar embeddings para vídeos existentes

Busca todos os bookmarks sem embedding e gera em lote.
Processa 10 vídeos por vez para evitar rate limits.

Uso:
    python generate_embeddings_backfill.py [--limit N] [--dry-run]

Exemplos:
    python generate_embeddings_backfill.py                # Processar todos
    python generate_embeddings_backfill.py --limit 50     # Processar apenas 50
    python generate_embeddings_backfill.py --dry-run      # Simular sem salvar
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# ⚠️ IMPORTANTE: Carregar env vars ANTES de importar services
load_dotenv()

from supabase import create_client, Client
from services.embedding_service import embedding_service
import time

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def main():
    parser = argparse.ArgumentParser(description='Gerar embeddings para vídeos existentes')
    parser.add_argument('--limit', type=int, help='Número máximo de vídeos a processar')
    parser.add_argument('--dry-run', action='store_true', help='Simular sem salvar no banco')
    args = parser.parse_args()

    # Conectar ao Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print(f"{Colors.RED}❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não configuradas{Colors.RESET}")
        sys.exit(1)

    supabase: Client = create_client(supabase_url, supabase_key)

    # Buscar vídeos sem embedding
    print(f"{Colors.BLUE}🔍 Buscando vídeos sem embedding...{Colors.RESET}")

    query = supabase.table('bookmarks').select('id, smart_title, auto_tags, auto_categories').is_('embedding', 'null')

    if args.limit:
        query = query.limit(args.limit)

    response = query.execute()
    videos = response.data

    if not videos:
        print(f"{Colors.GREEN}✅ Todos os vídeos já têm embedding!{Colors.RESET}")
        return

    total = len(videos)
    print(f"{Colors.YELLOW}📊 Encontrados {total} vídeos sem embedding{Colors.RESET}\n")

    if args.dry_run:
        print(f"{Colors.YELLOW}🔸 MODO DRY-RUN - Nenhuma alteração será salva{Colors.RESET}\n")

    # Processar em lote (10 por vez para evitar rate limits)
    BATCH_SIZE = 10
    success_count = 0
    error_count = 0

    for i, video in enumerate(videos):
        video_id = video['id']
        smart_title = (video.get('smart_title') or 'Sem título')[:60]

        print(f"[{i+1}/{total}] {smart_title}... ", end='', flush=True)

        try:
            # Buscar dados completos do vídeo
            full_video = supabase.table('bookmarks').select(
                'smart_title, auto_tags, auto_categories, video_transcript, visual_analysis'
            ).eq('id', video_id).single().execute()

            if not full_video.data:
                print(f"{Colors.RED}❌ Não encontrado{Colors.RESET}")
                error_count += 1
                continue

            # Gerar embedding
            embedding = embedding_service.generate_from_bookmark_dict(full_video.data)

            if not embedding:
                print(f"{Colors.RED}❌ Falha ao gerar{Colors.RESET}")
                error_count += 1
                continue

            # Salvar no banco (se não for dry-run)
            if not args.dry_run:
                supabase.table('bookmarks').update({
                    'embedding': embedding
                }).eq('id', video_id).execute()

            print(f"{Colors.GREEN}✅ ({len(embedding)}D){Colors.RESET}")
            success_count += 1

            # Rate limit: aguardar 1s a cada 10 vídeos
            if (i + 1) % BATCH_SIZE == 0 and (i + 1) < total:
                print(f"{Colors.YELLOW}⏸️  Aguardando 2s (rate limit)...{Colors.RESET}")
                time.sleep(2)

        except Exception as e:
            print(f"{Colors.RED}❌ Erro: {str(e)[:50]}{Colors.RESET}")
            error_count += 1

    # Resumo final
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.GREEN}✅ Sucesso: {success_count}/{total}{Colors.RESET}")
    if error_count > 0:
        print(f"{Colors.RED}❌ Erros: {error_count}/{total}{Colors.RESET}")

    if args.dry_run:
        print(f"{Colors.YELLOW}🔸 Modo dry-run - Nenhuma alteração foi salva{Colors.RESET}")


if __name__ == '__main__':
    main()
