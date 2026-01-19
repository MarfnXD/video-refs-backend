"""
Testa se o Apify está retornando URL corrompida
"""
import os
import asyncio
from dotenv import load_dotenv
from services.apify_service import ApifyService

load_dotenv()

async def main():
    apify = ApifyService()
    
    url = "https://www.instagram.com/share/reel/BAA5QBEBO5"
    
    print("=" * 80)
    print("🔍 TESTANDO EXTRAÇÃO DIRETA DO APIFY")
    print("=" * 80)
    print()
    
    print(f"URL: {url}")
    print()
    
    # Extrair metadados
    metadata = await apify.extract_instagram_reel(url)
    
    print(f"thumbnail_url retornado: {metadata.thumbnail_url}")
    print()
    
    if 'supabase' in metadata.thumbnail_url.lower():
        print("❌ APIFY RETORNOU URL CORROMPIDA!")
        print("   O Apify/Instagram está retornando URL do Supabase em vez do CDN original!")
    else:
        print("✅ APIFY retornou Instagram CDN correto")
    
    print()
    print("=" * 80)

asyncio.run(main())
