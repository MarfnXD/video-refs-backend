#!/usr/bin/env python3
"""
Script para analisar retroativamente os 10 vídeos mais recentes que já foram baixados.

Busca bookmarks com cloud_video_url (já baixados) mas SEM video_transcript (ainda não analisados).
Para cada um:
  1. Baixa vídeo temporariamente da cloud
  2. Analisa com Whisper (áudio) + GPT-4 Vision (frames)
  3. Salva transcrição + análise visual no Supabase
  4. Limpa arquivo temporário

Custo estimado: ~$0.01-0.02 por vídeo
"""

import os
import sys
import asyncio
import httpx
import tempfile
from datetime import datetime
from supabase import create_client, Client

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.video_analysis_service import video_analysis_service

# Configuração
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY devem estar configuradas!")
    sys.exit(1)

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY não configurada! Análise multimodal requer OpenAI API.")
    sys.exit(1)

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


async def download_video_from_cloud(cloud_url: str, output_path: str) -> bool:
    """
    Baixa vídeo da cloud temporariamente.

    Args:
        cloud_url: URL do vídeo no Supabase Storage (signed URL)
        output_path: Caminho local para salvar

    Returns:
        True se sucesso, False se falhar
    """
    try:
        print(f"  📥 Baixando vídeo da cloud...")

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(cloud_url)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ✅ Vídeo baixado: {file_size_mb:.2f}MB")
        return True

    except Exception as e:
        print(f"  ❌ Erro ao baixar vídeo: {str(e)}")
        return False


async def analyze_and_update_bookmark(bookmark: dict, index: int, total: int) -> bool:
    """
    Analisa um bookmark e atualiza no Supabase.

    Args:
        bookmark: Dados do bookmark
        index: Índice atual (1-based)
        total: Total de bookmarks

    Returns:
        True se sucesso, False se falhar
    """
    bookmark_id = bookmark['id']
    title = bookmark['title']
    cloud_url = bookmark['cloud_video_url']

    print(f"\n{'='*70}")
    print(f"📹 [{index}/{total}] {title[:60]}")
    print(f"   ID: {bookmark_id}")
    print(f"{'='*70}")

    # Cria arquivo temporário
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    temp_path = temp_file.name
    temp_file.close()

    try:
        # 1. Baixa vídeo da cloud
        if not await download_video_from_cloud(cloud_url, temp_path):
            return False

        # 2. Analisa vídeo (Whisper + GPT-4 Vision)
        print(f"  🎤🖼️  Analisando vídeo (áudio + visual)...")

        if not video_analysis_service.is_available():
            print("  ❌ VideoAnalysisService não disponível!")
            return False

        video_analysis = await video_analysis_service.analyze_video(temp_path)

        if not video_analysis:
            print("  ❌ Análise retornou vazio!")
            return False

        video_transcript = video_analysis.get("transcript", "")
        visual_analysis = video_analysis.get("visual_analysis", "")
        transcript_language = video_analysis.get("language", "")

        print(f"  ✅ Análise concluída!")
        print(f"     - Transcrição: {len(video_transcript)} chars ({transcript_language})")
        print(f"     - Análise Visual: {len(visual_analysis)} chars")

        # 3. Atualiza no Supabase
        print(f"  💾 Salvando no Supabase...")

        update_data = {
            'video_transcript': video_transcript if video_transcript else None,
            'visual_analysis': visual_analysis if visual_analysis else None,
            'transcript_language': transcript_language if transcript_language else None,
            'analyzed_at': datetime.utcnow().isoformat()
        }

        supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

        print(f"  ✅ Bookmark atualizado!")
        return True

    except Exception as e:
        print(f"  ❌ Erro ao processar bookmark: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Limpa arquivo temporário
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                print(f"  🗑️  Arquivo temporário removido")
            except:
                pass


async def main():
    """
    Busca e analisa os 10 vídeos mais recentes que já foram baixados mas ainda não analisados.
    """
    print("\n🚀 ANÁLISE RETROATIVA - 10 VÍDEOS MAIS RECENTES")
    print("="*70)

    # Busca bookmarks com cloud_video_url MAS sem video_transcript
    print("\n📊 Buscando vídeos para analisar...")
    print("   Critérios:")
    print("   - Tem cloud_video_url (já baixado)")
    print("   - NÃO tem video_transcript (ainda não analisado)")
    print("   - Ordenado por created_at DESC (mais recentes primeiro)")
    print("   - Limite: 10 vídeos")
    print()

    response = supabase.table("bookmarks") \
        .select("*") \
        .not_.is_('cloud_video_url', 'null') \
        .is_('video_transcript', 'null') \
        .order('created_at', desc=True) \
        .limit(10) \
        .execute()

    bookmarks = response.data

    if not bookmarks:
        print("✅ Nenhum vídeo para analisar! Todos os vídeos baixados já foram analisados.")
        return

    total = len(bookmarks)
    print(f"📦 {total} vídeos encontrados para análise\n")

    # Confirma com usuário
    print(f"⚠️  AVISO: Isso vai custar aproximadamente ${total * 0.015:.2f} USD (Whisper + GPT-4 Vision)")
    print()
    response = input("Continuar? (s/N): ")
    if response.lower() != 's':
        print("❌ Cancelado pelo usuário")
        return

    # Processa cada bookmark
    success_count = 0
    failed_count = 0

    for i, bookmark in enumerate(bookmarks, 1):
        result = await analyze_and_update_bookmark(bookmark, i, total)

        if result:
            success_count += 1
        else:
            failed_count += 1

        # Pausa entre requisições (evita rate limiting)
        if i < total:
            await asyncio.sleep(2)

    # Resumo final
    print(f"\n{'='*70}")
    print(f"🎉 ANÁLISE CONCLUÍDA!")
    print(f"{'='*70}")
    print(f"✅ Sucesso: {success_count}/{total}")
    print(f"❌ Falhas: {failed_count}/{total}")
    print(f"💰 Custo estimado: ~${success_count * 0.015:.2f} USD")
    print()

    if success_count > 0:
        print("📝 PRÓXIMOS PASSOS:")
        print("   1. Regenerar embeddings para incluir transcrição + visual:")
        print("      python3 generate_embeddings.py")
        print()
        print("   2. Testar busca semântica no app")
        print()


if __name__ == "__main__":
    asyncio.run(main())
