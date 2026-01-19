#!/usr/bin/env python3
"""
Diagnóstico do pipeline - Simula execução local e mostra onde falha
"""
import os
import asyncio
from dotenv import load_dotenv

# IMPORTANTE: Carregar .env ANTES de qualquer import de services
load_dotenv()

from supabase import create_client, Client
from services.apify_service import ApifyService
from services.gemini_service import gemini_service
from models import Platform

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

apify_service = ApifyService()

class Colors:
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    WARNING = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

async def diagnose_video_analysis(bookmark_id: str):
    """Diagnostica por que a análise de vídeo não executou"""

    print(f"\n{Colors.BOLD}🔍 DIAGNÓSTICO: {bookmark_id}{Colors.ENDC}\n")

    # 1. Buscar bookmark no DB
    print("1️⃣ Consultando bookmark no Supabase...")
    result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).execute()

    if not result.data or len(result.data) == 0:
        print(f"{Colors.FAIL}❌ Bookmark não encontrado{Colors.ENDC}")
        return

    bookmark = result.data[0]
    url = bookmark['url']
    platform = bookmark.get('platform', 'unknown')

    print(f"{Colors.OKGREEN}✓ Bookmark encontrado{Colors.ENDC}")
    print(f"   URL: {url}")
    print(f"   Platform: {platform}")
    print(f"   Status: {bookmark.get('processing_status')}")

    # 2. Verificar se tem cloud_video_url
    print(f"\n2️⃣ Verificando cloud_video_url...")
    cloud_url = bookmark.get('cloud_video_url')

    if cloud_url:
        print(f"{Colors.OKGREEN}✓ Tem cloud_video_url: {cloud_url[:60]}...{Colors.ENDC}")
        video_url_for_analysis = cloud_url
    else:
        print(f"{Colors.WARNING}⚠️  Sem cloud_video_url - Tentando baixar via Apify...{Colors.ENDC}")

        # 3. Tentar extrair URL de download via Apify
        print(f"\n3️⃣ Extraindo URL de download via Apify...")

        try:
            platform_enum = apify_service.detect_platform(url)
            print(f"   Platform detectada: {platform_enum}")

            if platform_enum == Platform.YOUTUBE:
                print(f"   Chamando: extract_video_download_url_youtube()")
                video_data = await apify_service.extract_video_download_url_youtube(url, quality="720p")
            elif platform_enum == Platform.INSTAGRAM:
                print(f"   Chamando: extract_video_download_url_instagram()")
                video_data = await apify_service.extract_video_download_url_instagram(url, quality="720p")
            elif platform_enum == Platform.TIKTOK:
                print(f"   Chamando: extract_video_download_url_tiktok()")
                video_data = await apify_service.extract_video_download_url_tiktok(url, quality="720p")
            else:
                print(f"{Colors.FAIL}❌ Plataforma não suportada: {platform_enum}{Colors.ENDC}")
                return

            if video_data and video_data.get('download_url'):
                video_url_for_analysis = video_data['download_url']
                print(f"{Colors.OKGREEN}✓ URL extraída: {video_url_for_analysis[:80]}...{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ Apify não retornou download_url{Colors.ENDC}")
                print(f"   Resposta: {video_data}")
                return

        except Exception as e:
            print(f"{Colors.FAIL}❌ ERRO ao extrair URL: {e}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            return

    # 4. Tentar analisar com Gemini
    print(f"\n4️⃣ Testando análise Gemini...")
    print(f"   URL para análise: {video_url_for_analysis[:80]}...")

    try:
        user_context = bookmark.get('user_context', '')
        print(f"   User context: {'✓' if user_context else '✗'}")

        print(f"   Chamando: gemini_service.analyze_video()")
        gemini_analysis = await gemini_service.analyze_video(video_url_for_analysis, user_context)

        if gemini_analysis:
            print(f"{Colors.OKGREEN}✓ Gemini analisou com sucesso!{Colors.ENDC}")
            print(f"   Idioma: {gemini_analysis.get('language')}")
            print(f"   Transcript: {len(gemini_analysis.get('transcript', ''))} chars")
            print(f"   Visual analysis: {len(gemini_analysis.get('visual_analysis', ''))} chars")
            print(f"   FOOH: {gemini_analysis.get('is_fooh')}")
        else:
            print(f"{Colors.FAIL}❌ Gemini retornou None{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}❌ ERRO ao analisar com Gemini: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n{Colors.OKGREEN}{'='*70}")
    print(f"✅ DIAGNÓSTICO COMPLETO - Pipeline funcionaria localmente!")
    print(f"{'='*70}{Colors.ENDC}\n")

async def main():
    # Pegar último bookmark processado
    result = supabase.table('bookmarks').select('id').order('created_at', desc=True).limit(1).execute()

    if result.data and len(result.data) > 0:
        bookmark_id = result.data[0]['id']
        await diagnose_video_analysis(bookmark_id)
    else:
        print("❌ Nenhum bookmark encontrado")

if __name__ == "__main__":
    asyncio.run(main())
