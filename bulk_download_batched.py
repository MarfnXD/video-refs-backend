#!/usr/bin/env python3
"""
Script de download em massa com BATCHES Apify (8x mais rápido!)
Usa batches de 10 URLs por actor = reduz overhead drasticamente
"""

import asyncio
import aiohttp
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from supabase import create_client, Client
from tqdm.asyncio import tqdm
from apify_client import ApifyClient
import argparse

# Configurações
BACKEND_URL = os.getenv("BACKEND_URL", "https://video-refs-backend.onrender.com")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo")

# Diretório local para salvar vídeos temporariamente
TEMP_DIR = Path("./temp_downloads")
TEMP_DIR.mkdir(exist_ok=True)

# Estatísticas globais
stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
}

class BatchDownloadManager:
    def __init__(self, user_id: str, apify_tokens: List[str], parallel: int = 10,
                 batch_size: int = 10, quality: str = '720p'):
        self.user_id = user_id
        self.apify_tokens = apify_tokens
        self.parallel = parallel
        self.batch_size = batch_size
        self.quality = quality
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.session: Optional[aiohttp.ClientSession] = None

        # Cria clientes Apify
        self.apify_clients = [ApifyClient(token) for token in apify_tokens]
        self.current_client_index = 0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def _get_next_apify_client(self) -> ApifyClient:
        """Rotaciona entre clientes Apify"""
        client = self.apify_clients[self.current_client_index]
        self.current_client_index = (self.current_client_index + 1) % len(self.apify_clients)
        return client

    async def get_pending_bookmarks(self) -> List[Dict]:
        """Busca bookmarks sem vídeo baixado"""
        print(f"\n🔍 Buscando bookmarks sem vídeo para user: {self.user_id[:8]}...")

        response = self.supabase.table('bookmarks').select('*').eq('user_id', self.user_id).is_('cloud_video_url', 'null').execute()

        bookmarks = response.data

        # Filtra apenas Instagram/TikTok (YouTube não precisa de Apify batching)
        instagram_bookmarks = [b for b in bookmarks if 'instagram.com' in b['url']]
        tiktok_bookmarks = [b for b in bookmarks if 'tiktok.com' in b['url']]

        print(f"✅ Encontrados {len(instagram_bookmarks)} Instagram + {len(tiktok_bookmarks)} TikTok para baixar\n")

        stats['total'] = len(instagram_bookmarks) + len(tiktok_bookmarks)
        return instagram_bookmarks + tiktok_bookmarks

    async def process_via_backend(self, bookmarks: List[Dict], pbar: tqdm):
        """Processa vídeos via backend (Apify + transcode + download)"""
        # Semáforo para limitar paralelismo
        semaphore = asyncio.Semaphore(self.parallel)

        async def download_with_semaphore(bookmark):
            async with semaphore:
                result = await self.download_via_backend(bookmark, pbar)
                pbar.update(1)

                # Delay entre downloads
                await asyncio.sleep(2)
                return result

        # Executa downloads em paralelo
        tasks = [download_with_semaphore(b) for b in bookmarks]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def download_via_backend(self, bookmark: Dict, pbar: tqdm) -> bool:
        """
        Backend faz TUDO: Apify + download + FFmpeg + upload para Supabase.
        Vídeo NÃO trafega para o PC - tudo server-side! 🚀
        """
        bookmark_id = bookmark['id']
        url = bookmark['url']
        title = bookmark.get('title', 'Sem título')[:50]

        try:
            # Backend faz TUDO: Apify → Download → FFmpeg → Upload Supabase
            pbar.set_description(f"🚀 {title}")

            async with self.session.post(
                f"{BACKEND_URL}/api/process-to-supabase",
                json={
                    'url': url,
                    'user_id': self.user_id,
                    'bookmark_id': bookmark_id,
                    'quality': self.quality
                },
                timeout=aiohttp.ClientTimeout(total=300)  # 5 min (pode demorar)
            ) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    raise Exception(f"Backend retornou {resp.status}: {error_data.get('error', 'Erro desconhecido')}")

                data = await resp.json()

                if not data.get('success'):
                    raise Exception(data.get('error', 'Processamento falhou'))

                # Sucesso! Backend já fez tudo (Apify, FFmpeg, Upload, DB update)
                file_size_mb = data.get('file_size_mb', 0)

            stats['success'] += 1
            pbar.set_description(f"✅ {title} ({file_size_mb:.1f}MB)")
            return True

        except Exception as e:
            stats['failed'] += 1
            pbar.set_description(f"❌ {title[:30]}: {str(e)[:20]}")

            # Log de erro
            with open('download_errors.log', 'a') as f:
                f.write(f"{datetime.now()} | {bookmark_id} | {url} | {str(e)}\n")

            return False

    async def download_video(self, bookmark: Dict, download_url: str, pbar: tqdm) -> bool:
        """Baixa um vídeo individual (já tem a URL)"""
        bookmark_id = bookmark['id']
        title = bookmark.get('title', 'Sem título')[:50]

        try:
            # 1. Baixar arquivo
            pbar.set_description(f"⬇️  {title}")

            filename = f"{bookmark_id}.mp4"
            filepath = TEMP_DIR / filename

            async with self.session.get(download_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    raise Exception(f"Download falhou: {resp.status}")

                with open(filepath, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)

            file_size = filepath.stat().st_size

            # 2. Upload para Supabase Storage
            pbar.set_description(f"☁️  {title}")

            with open(filepath, 'rb') as f:
                storage_path = f"{self.user_id}/{bookmark_id}.mp4"

                self.supabase.storage.from_('user-videos').upload(
                    storage_path,
                    f,
                    file_options={"content-type": "video/mp4"}
                )

            # Gera URL assinada (válida por 1 ano)
            cloud_url = self.supabase.storage.from_('user-videos').create_signed_url(
                storage_path,
                expires_in=31536000  # 1 ano
            )['signedURL']

            # 3. Atualizar bookmark no Supabase
            self.supabase.table('bookmarks').update({
                'cloud_video_url': cloud_url,
                'cloud_upload_status': 'completed',
                'cloud_uploaded_at': datetime.utcnow().isoformat(),
                'cloud_file_size_bytes': file_size,
                'video_quality': self.quality,
            }).eq('id', bookmark_id).execute()

            # Limpar arquivo temporário
            filepath.unlink()

            stats['success'] += 1
            pbar.set_description(f"✅ {title}")
            return True

        except Exception as e:
            stats['failed'] += 1
            pbar.set_description(f"❌ {title[:30]}: {str(e)[:20]}")

            # Log de erro
            with open('download_errors.log', 'a') as f:
                f.write(f"{datetime.now()} | {bookmark_id} | {bookmark['url']} | {str(e)}\n")

            return False

    async def process_downloads(self, bookmarks: List[Dict], url_mapping: Dict[str, str]):
        """Processa downloads em paralelo (após extração em batch)"""
        with tqdm(total=len(bookmarks), desc="📥 Downloads", unit="vídeo") as pbar:
            # Semáforo para limitar paralelismo
            semaphore = asyncio.Semaphore(self.parallel)

            async def download_with_semaphore(bookmark):
                async with semaphore:
                    bookmark_url = bookmark['url']

                    # Normalizar URL: Instagram usa /reel/ e /p/ para o mesmo conteúdo
                    # Apify sempre retorna /p/, então normalizamos os bookmarks também
                    normalized_url = bookmark_url.replace('/reel/', '/p/')

                    download_url = url_mapping.get(normalized_url)

                    if not download_url:
                        stats['failed'] += 1
                        pbar.update(1)
                        return False

                    result = await self.download_video(bookmark, download_url, pbar)
                    pbar.update(1)

                    # Delay entre downloads
                    await asyncio.sleep(1)
                    return result

            # Executa downloads em paralelo
            tasks = [download_with_semaphore(b) for b in bookmarks]
            await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    parser = argparse.ArgumentParser(description='Download em massa com BATCHES (8x mais rápido!)')
    parser.add_argument('--user-id', required=True, help='ID do usuário no Supabase')
    parser.add_argument('--apify-tokens', required=True, help='Tokens Apify separados por vírgula')
    parser.add_argument('--parallel', type=int, default=10, help='Downloads simultâneos (padrão: 10)')
    parser.add_argument('--batch-size', type=int, default=10, help='URLs por batch Apify (padrão: 10)')
    parser.add_argument('--quality', default='720p', choices=['480p', '720p', '1080p'], help='Qualidade do vídeo')
    parser.add_argument('--limit', type=int, help='Limitar número de downloads (para teste)')

    args = parser.parse_args()

    apify_tokens = [t.strip() for t in args.apify_tokens.split(',')]

    print("=" * 80)
    print("🚀 VIDEO REFS - BATCH DOWNLOAD (8x MAIS RÁPIDO)".center(80))
    print("=" * 80)
    print(f"\n⚙️  Configurações:")
    print(f"   User ID: {args.user_id[:8]}...")
    print(f"   Apify Accounts: {len(apify_tokens)} contas")
    print(f"   Batch Size: {args.batch_size} URLs/batch")
    print(f"   Paralelismo Downloads: {args.parallel} simultâneos")
    print(f"   Qualidade: {args.quality}")

    start_time = datetime.now()

    async with BatchDownloadManager(args.user_id, apify_tokens, args.parallel, args.batch_size, args.quality) as manager:
        # Buscar bookmarks pendentes
        bookmarks = await manager.get_pending_bookmarks()

        if not bookmarks:
            print("✅ Nenhum vídeo pendente! Todos já foram baixados.")
            return

        # Limitar se especificado (para testes)
        if args.limit:
            bookmarks = bookmarks[:args.limit]
            print(f"⚠️  Limitado a {args.limit} vídeos (modo teste)\n")

        # Processamento via backend (Apify + Transcode + Upload)
        print("\n" + "=" * 80)
        print("BACKEND → SUPABASE (Apify + FFmpeg + Upload)".center(80))
        print("=" * 80)

        # Progress bar unificada
        with tqdm(total=len(bookmarks), desc="📥 Processando", unit="vídeo") as pbar:
            await manager.process_via_backend(bookmarks, pbar)

    # Estatísticas finais
    duration = datetime.now() - start_time

    print("\n" + "=" * 80)
    print("📊 ESTATÍSTICAS FINAIS".center(80))
    print("=" * 80)
    print(f"⏱️  Tempo total: {duration}")
    print(f"📹 Total processado: {stats['total']}")
    print(f"✅ Sucesso: {stats['success']}")
    print(f"❌ Falhas: {stats['failed']}")
    if stats['success'] > 0:
        print(f"⚡ Velocidade: {stats['success'] / duration.total_seconds() * 60:.1f} vídeos/hora")

    if stats['failed'] > 0:
        print(f"\n⚠️  Veja erros em: download_errors.log")

    print("=" * 80)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrompido pelo usuário")
        print(f"✅ Sucesso até agora: {stats['success']}")
        print(f"❌ Falhas: {stats['failed']}")
        sys.exit(0)
