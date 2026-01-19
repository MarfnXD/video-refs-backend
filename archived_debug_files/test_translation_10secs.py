"""
Script para reprocessar o vídeo "10 Secs practice ? aight." com tradução automática
"""
import os
import sys
from supabase import create_client, Client
from services.video_analysis_service import video_analysis_service
from datetime import datetime

# Configuração
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

async def find_and_reprocess():
    print("\n🔍 Buscando vídeo '10 Secs practice ? aight.'...")
    print("=" * 70)

    # Buscar bookmark pelo título
    response = supabase.table("bookmarks").select("*").ilike("title", "%10 Secs practice%").execute()

    if not response.data or len(response.data) == 0:
        print("❌ Vídeo não encontrado!")
        return

    bookmark = response.data[0]
    print(f"✅ Vídeo encontrado!")
    print(f"   ID: {bookmark['id']}")
    print(f"   Título: {bookmark['title']}")
    print(f"   URL: {bookmark['url']}")
    print(f"   Plataforma: {bookmark['platform']}")

    # Verifica se tem vídeo na cloud
    cloud_video_url = bookmark.get('cloud_video_url')
    if not cloud_video_url:
        print(f"\n❌ Vídeo não está na cloud (cloud_video_url vazio)")
        print(f"   Você precisa fazer upload do vídeo para o Supabase primeiro!")
        return

    # Baixar vídeo da cloud para processamento temporário
    print(f"\n☁️  Baixando vídeo da cloud do Supabase...")
    import httpx
    import tempfile

    temp_video_path = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(cloud_video_url)
        response.raise_for_status()

        with open(temp_video_path, 'wb') as f:
            f.write(response.content)

    print(f"✅ Vídeo baixado temporariamente: {temp_video_path}")
    print(f"   Tamanho: {os.path.getsize(temp_video_path) / 1024 / 1024:.2f} MB")

    local_video_path = temp_video_path

    # Reprocessar com análise multimodal + tradução
    print(f"\n🎬 Iniciando análise multimodal + tradução automática...")
    print("-" * 70)

    if not video_analysis_service.is_available():
        print("❌ OpenAI API não configurada!")
        return

    analysis_result = await video_analysis_service.analyze_video(local_video_path)

    if not analysis_result:
        print("❌ Falha na análise do vídeo")
        return

    print(f"\n✅ ANÁLISE CONCLUÍDA!")
    print("=" * 70)

    # Transcrição original
    transcript = analysis_result.get("transcript", "")
    transcript_pt = analysis_result.get("transcript_pt")
    language = analysis_result.get("language", "")

    print(f"\n🎤 TRANSCRIÇÃO:")
    print(f"   Idioma detectado: {language.upper()}")
    print(f"   Tamanho original: {len(transcript)} caracteres")
    if transcript_pt:
        print(f"   Tamanho traduzido: {len(transcript_pt)} caracteres")
    print(f"\n   Original ({language.upper()}):")
    print(f"   {transcript[:200]}...")
    if transcript_pt:
        print(f"\n   🌐 Tradução (PT):")
        print(f"   {transcript_pt[:200]}...")

    # Análise visual
    visual = analysis_result.get("visual_analysis", "")
    visual_pt = analysis_result.get("visual_analysis_pt")

    print(f"\n👁️  ANÁLISE VISUAL:")
    print(f"   Tamanho original: {len(visual)} caracteres")
    if visual_pt:
        print(f"   Tamanho traduzido: {len(visual_pt)} caracteres")
    print(f"\n   Original (EN):")
    print(f"   {visual[:200]}...")
    if visual_pt:
        print(f"\n   🌐 Tradução (PT):")
        print(f"   {visual_pt[:200]}...")

    # Atualizar no Supabase
    print(f"\n💾 Salvando no Supabase...")
    update_data = {
        'video_transcript': transcript,
        'visual_analysis': visual,
        'transcript_language': language,
        'analyzed_at': datetime.utcnow().isoformat(),
    }

    if transcript_pt:
        update_data['video_transcript_pt'] = transcript_pt
    if visual_pt:
        update_data['visual_analysis_pt'] = visual_pt

    supabase.table('bookmarks').update(update_data).eq('id', bookmark['id']).execute()

    print(f"✅ Bookmark atualizado com sucesso!")
    print("=" * 70)

    # Limpar arquivo temporário
    try:
        os.unlink(temp_video_path)
        print(f"\n🗑️  Arquivo temporário removido")
    except:
        pass

    # Resumo final
    print(f"\n📊 RESUMO:")
    print(f"   ✅ Transcrição: {len(transcript)} chars ({language.upper()})")
    if transcript_pt:
        print(f"   ✅ Transcrição PT: {len(transcript_pt)} chars")
    print(f"   ✅ Análise Visual: {len(visual)} chars (EN)")
    if visual_pt:
        print(f"   ✅ Análise Visual PT: {len(visual_pt)} chars")
    print(f"\n🎉 TRADUÇÃO AUTOMÁTICA FUNCIONANDO!")
    print("=" * 70)

if __name__ == "__main__":
    import asyncio
    asyncio.run(find_and_reprocess())
