#!/usr/bin/env python3
"""
Teste do método extract_all_instagram_comments()
Extrai TODOS os comentários de um post do Instagram (ordenados por likes)
"""
import asyncio
import os
import sys

# Carregar .env ANTES de qualquer import
from dotenv import load_dotenv
load_dotenv()

# Agora importar serviços
from services.apify_service import ApifyService

async def test():
    apify = ApifyService()

    url = 'https://www.instagram.com/reel/DPHYVUwD7D0/?igsh=ancyZGlwbXZsNWx1'

    print('🔄 Testando EXTRAÇÃO COMPLETA de comentários...')
    print(f'URL: {url}')
    print(f'Limite: 100 comentários (teste)')
    print(f'Custo estimado: ${(100 / 1000) * 2.30:.2f}\n')

    try:
        comments = await apify.extract_all_instagram_comments(url, max_comments=100)

        print(f'\n✅ EXTRAÇÃO COMPLETA CONCLUÍDA!')
        print(f'   Total: {len(comments)} comentários extraídos')

        if len(comments) > 0:
            print(f'\n📝 Top 10 comentários (ordenados por likes):')
            for i, comment in enumerate(comments[:10], 1):
                print(f'{i}. "{comment.text[:80]}" ({comment.likes:,} likes) by {comment.author}')

            # Buscar comentário específico
            print(f'\n🔍 Buscando "remix" e "trend"...')
            found = False
            for comment in comments:
                if 'remix' in comment.text.lower() and 'trend' in comment.text.lower():
                    print(f'\n🎯 ENCONTRADO!')
                    print(f'   Texto: "{comment.text}"')
                    print(f'   Likes: {comment.likes:,}')
                    print(f'   Autor: {comment.author}')
                    found = True
                    break

            if not found:
                print(f'❌ NÃO encontrado nos {len(comments)} comentários')

                # Mostrar alguns exemplos de comentários extraídos
                print(f'\n📊 Exemplos de comentários extraídos:')
                for i, comment in enumerate(comments[10:20], 11):
                    print(f'{i}. "{comment.text[:60]}..." ({comment.likes} likes)')
        else:
            print('❌ Nenhum comentário extraído!')

    except Exception as e:
        print(f'❌ ERRO: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test())
