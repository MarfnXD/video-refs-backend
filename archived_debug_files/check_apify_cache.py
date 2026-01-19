"""
Verifica se o cache do Apify está corrompido
"""
import os
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv('REDIS_URL')

if not REDIS_URL:
    print("❌ REDIS_URL não configurada")
    exit(1)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

url = "https://www.instagram.com/share/reel/BAA5QBEBO5"
cache_key = f"instagram:{url}"

print("=" * 80)
print("🔍 VERIFICANDO CACHE DO APIFY")
print("=" * 80)
print()

print(f"Cache key: {cache_key}")
print()

cached = redis_client.get(cache_key)

if cached:
    print("✅ Cache encontrado!")
    print()
    import json
    data = json.loads(cached)
    
    print(f"thumbnail_url no cache: {data.get('thumbnail_url')}")
    print()
    
    if 'supabase' in data.get('thumbnail_url', '').lower():
        print("❌ CACHE CORROMPIDO! Thumbnail no cache já está com URL do Supabase!")
        print()
        print("Isso explica o bug - o Apify está retornando metadados corrompidos do cache!")
    else:
        print("✅ Cache está correto (Instagram CDN)")
else:
    print("❌ Cache não encontrado")

print()
print("=" * 80)
