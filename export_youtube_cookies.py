#!/usr/bin/env python3
"""
Exporta cookies do YouTube do Chrome local e sobe pro Supabase Storage.
O backend usa esses cookies pro yt-dlp baixar videos do YouTube.

Uso:
    python3 export_youtube_cookies.py

Cookies duram ~2 anos. Rodar novamente so quando o backend avisar que expiraram.
"""
import subprocess
import os
import sys
from datetime import datetime
from supabase import create_client

SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"
COOKIES_PATH = "/tmp/youtube_cookies.txt"
STORAGE_BUCKET = "thumbnails"  # Reusa bucket existente
STORAGE_KEY = "system/youtube_cookies.txt"


def export_cookies():
    """Exporta cookies do YouTube usando yt-dlp --cookies-from-browser"""
    print("🍪 Exportando cookies do YouTube do Chrome...")

    # yt-dlp exporta cookies no formato Netscape
    result = subprocess.run(
        [
            "yt-dlp",
            "--cookies-from-browser", "chrome",
            "--cookies", COOKIES_PATH,
            "--skip-download",
            "--no-warnings",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # URL dummy so pra exportar
        ],
        capture_output=True, text=True, timeout=30
    )

    if not os.path.exists(COOKIES_PATH):
        print(f"❌ Falha ao exportar cookies: {result.stderr[:200]}")
        sys.exit(1)

    size = os.path.getsize(COOKIES_PATH)
    print(f"✅ Cookies exportados: {COOKIES_PATH} ({size // 1024}KB)")

    # Contar cookies do YouTube
    with open(COOKIES_PATH) as f:
        yt_cookies = [l for l in f if ".youtube.com" in l and not l.startswith("#")]
    print(f"   {len(yt_cookies)} cookies do YouTube encontrados")

    if len(yt_cookies) < 3:
        print("⚠️ Poucos cookies! Certifique-se de estar logado no YouTube no Chrome.")
        sys.exit(1)

    return COOKIES_PATH


def upload_to_supabase(file_path: str):
    """Sobe cookies pro Supabase Storage"""
    print(f"☁️ Fazendo upload pro Supabase Storage...")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    with open(file_path, "rb") as f:
        content = f.read()

    # Upload com upsert
    sb.storage.from_(STORAGE_BUCKET).upload(
        path=STORAGE_KEY,
        file=content,
        file_options={"content-type": "text/plain", "upsert": "true"}
    )

    print(f"✅ Upload OK: {STORAGE_BUCKET}/{STORAGE_KEY}")

    # Salvar timestamp no Redis (via backend) ou direto no storage
    # Salvamos como metadata: um arquivo JSON com a data
    meta = f'{{"exported_at": "{datetime.utcnow().isoformat()}", "size_bytes": {len(content)}}}'
    sb.storage.from_(STORAGE_BUCKET).upload(
        path="system/youtube_cookies_meta.json",
        file=meta.encode(),
        file_options={"content-type": "application/json", "upsert": "true"}
    )

    print(f"✅ Metadata salvo")


def main():
    print("=" * 50)
    print("YouTube Cookies Exporter → Supabase")
    print("=" * 50)

    file_path = export_cookies()
    upload_to_supabase(file_path)

    # Cleanup
    os.remove(file_path)

    print()
    print("🎉 Pronto! O backend vai usar esses cookies pro yt-dlp.")
    print("   Cookies duram ~2 anos. O app te avisa se expirarem.")


if __name__ == "__main__":
    main()
