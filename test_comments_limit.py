#!/usr/bin/env python3
"""Teste para verificar se commentsLimit funciona no Apify Instagram Scraper"""
import asyncio
import os
from dotenv import load_dotenv

# Carregar .env ANTES de imports
load_dotenv()

from services.apify_service import ApifyService

async def test():
    apify = ApifyService()

    url = "https://www.instagram.com/reel/DPHYVUwD7D0/?igsh=ancyZGlwbXZsNWx1"

    print("🔄 Testando extração de comentários...")
    print(f"URL: {url}\n")

    metadata = await apify.extract_instagram_reel(url)

    print(f"📊 Resultado:")
    print(f"   Total de comentários capturados: {len(metadata.top_comments)}")
    print(f"   Comentários totais no vídeo: {metadata.comments_count:,}\n")

    if len(metadata.top_comments) > 0:
        print("Top 5 comentários (ordenados por likes):")
        sorted_comments = sorted(
            metadata.top_comments,
            key=lambda x: x.likes,
            reverse=True
        )

        for i, comment in enumerate(sorted_comments[:5], 1):
            print(f"{i}. \"{comment.text[:60]}...\" ({comment.likes} likes)")

        # Buscar comentário específico
        print("\n🔍 Buscando 'remix' ou 'trend'...")
        for comment in metadata.top_comments:
            if 'remix' in comment.text.lower() or 'trend' in comment.text.lower():
                print(f"✅ ENCONTRADO: \"{comment.text}\" ({comment.likes} likes)")
                break
        else:
            print("❌ Não encontrado")
    else:
        print("❌ Nenhum comentário capturado!")

if __name__ == "__main__":
    asyncio.run(test())
