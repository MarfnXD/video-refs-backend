#!/usr/bin/env python3
"""
Script de download em massa paralelo para Video Refs
Usa Apify via backend + paralelismo controlado
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
import argparse

# Configurações
BACKEND_URL = "https://video-refs-backend.onrender.com"
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNzQ3MTQyMywiZXhwIjoyMDQzMDQ3NDIzfQ.D9CZq9TpZKR8MmTKzQRqAkVe0A6d_1eqgWw_7g5s5dw"

# Diretório local para salvar vídeos temporariamente
TEMP_DIR = Path("./temp_downloads")
TEMP_DIR.mkdir(exist_ok=True)

# Estatísticas globais
stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'skipped': 0,
    'apify_credits_used': 0,
}

class DownloadManager:
    def __init__(self, user_id: str, parallel: int = 5, quality: str = '720p'):
        self.user_id = user_id
        self.parallel = parallel
        self.quality = quality
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def get_pending_bookmarks(self) -> List[Dict]:
        """Busca bookmarks sem vídeo baixado"""
        print(f"\n🔍 Buscando bookmarks sem vídeo para user: {self.user_id[:8]}...")

        response = self.supabase.table('bookmarks').select('*').eq('user_id', self.user_id).is_('local_video_path', 'null').execute()

        bookmarks = response.data
        print(f"✅ Encontrados {len(bookmarks)} vídeos para baixar\n")

        stats['total'] = len(bookmarks)
        return bookmarks

    async def download_video(self, bookmark: Dict, pbar: tqdm) -> bool:
        """Baixa um vídeo individual"""
        bookmark_id = bookmark['id']
        url = bookmark['url']
        title = bookmark.get('title', 'Sem título')[:50]

        try:
            # 1. Extrair URL de download via backend (usa Apify)
            pbar.set_description(f"📡 {title}")

            async with self.session.post(
                f"{BACKEND_URL}/api/extract-video-download-url",
                json={
                    'url': url,
                    'quality': self.quality,
                    'transcode': False  # Modo rápido
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Backend retornou {resp.status}")

                data = await resp.json()

                if not data.get('success') or not data.get('download_url'):
                    raise Exception(data.get('error', 'URL não disponível'))

                download_url = data['download_url']

                # Incrementa contador de créditos Apify
                if 'apify' in str(data).lower():
                    stats['apify_credits_used'] += 150  # Estimativa

            # 2. Baixar arquivo
            pbar.set_description(f"⬇️  {title}")

            filename = f"{bookmark_id}.mp4"
            filepath = TEMP_DIR / filename

            async with self.session.get(download_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Download falhou: {resp.status}")

                with open(filepath, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)

            file_size = filepath.stat().st_size

            # 3. Upload para Supabase Storage
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

            # 4. Atualizar bookmark no Supabase
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
                f.write(f"{datetime.now()} | {bookmark_id} | {url} | {str(e)}\n")

            return False

    async def process_batch(self, bookmarks: List[Dict]):
        """Processa lote de downloads em paralelo"""
        with tqdm(total=len(bookmarks), desc="📥 Downloads", unit="vídeo") as pbar:
            # Semáforo para limitar paralelismo
            semaphore = asyncio.Semaphore(self.parallel)

            async def download_with_semaphore(bookmark):
                async with semaphore:
                    result = await self.download_video(bookmark, pbar)
                    pbar.update(1)

                    # Delay entre downloads para evitar sobrecarga
                    await asyncio.sleep(2)
                    return result

            # Executa downloads em paralelo
            tasks = [download_with_semaphore(b) for b in bookmarks]
            await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    parser = argparse.ArgumentParser(description='Download em massa de vídeos')
    parser.add_argument('--user-id', required=True, help='ID do usuário no Supabase')
    parser.add_argument('--parallel', type=int, default=5, help='Downloads simultâneos (padrão: 5)')
    parser.add_argument('--quality', default='720p', choices=['480p', '720p', '1080p'], help='Qualidade do vídeo')
    parser.add_argument('--limit', type=int, help='Limitar número de downloads (para teste)')

    args = parser.parse_args()

    print("=" * 80)
    print("🚀 VIDEO REFS - BULK DOWNLOAD PARALELO".center(80))
    print("=" * 80)
    print(f"\n⚙️  Configurações:")
    print(f"   User ID: {args.user_id[:8]}...")
    print(f"   Paralelismo: {args.parallel} simultâneos")
    print(f"   Qualidade: {args.quality}")
    print(f"   Backend: {BACKEND_URL}")

    start_time = datetime.now()

    async with DownloadManager(args.user_id, args.parallel, args.quality) as manager:
        # Buscar bookmarks pendentes
        bookmarks = await manager.get_pending_bookmarks()

        if not bookmarks:
            print("✅ Nenhum vídeo pendente! Todos já foram baixados.")
            return

        # Limitar se especificado (para testes)
        if args.limit:
            bookmarks = bookmarks[:args.limit]
            print(f"⚠️  Limitado a {args.limit} vídeos (modo teste)\n")

        # Processar downloads
        await manager.process_batch(bookmarks)

    # Estatísticas finais
    duration = datetime.now() - start_time

    print("\n" + "=" * 80)
    print("📊 ESTATÍSTICAS FINAIS".center(80))
    print("=" * 80)
    print(f"⏱️  Tempo total: {duration}")
    print(f"📹 Total processado: {stats['total']}")
    print(f"✅ Sucesso: {stats['success']}")
    print(f"❌ Falhas: {stats['failed']}")
    print(f"💳 Créditos Apify estimados: ~{stats['apify_credits_used']}")

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
