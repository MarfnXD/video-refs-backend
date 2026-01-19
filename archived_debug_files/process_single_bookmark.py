"""
Script para processar um único bookmark com análise multimodal completa

Etapas:
1. Busca bookmark por URL
2. Verifica se tem vídeo baixado (local_video_path)
3. Se tiver: roda análise multimodal (transcript + visual)
4. Recaptura metadados com 200 comentários
5. Reprocessa com IA (com transcript + visual + comentários)
6. Atualiza Supabase
7. Gera embedding
"""
import asyncio
from supabase import create_client
from services.apify_service import ApifyService
from services.claude_service import ClaudeService
from services.video_analysis_service import VideoAnalysisService

# Instanciar serviços
apify_service = ApifyService()
claude_service = ClaudeService()
video_analysis_service = VideoAnalysisService()
from openai import OpenAI
import os

# Configuração
SUPABASE_URL = "https://twwpcnyqpwznzarguzit.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMzA0MSwiZXhwIjoyMDc0NTA5MDQxfQ.wEit0wE8nWtnk9cZ6rnV1lqoe6pKsAbG9lK2C4dmMFo"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY não encontrada")
    exit(1)

supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# URL do FOOH
FOOH_URL = "https://www.instagram.com/reel/C9w7U5zqJeN/"


async def process_fooh_bookmark():
    """Processa bookmark FOOH com análise completa"""

    print("\n" + "=" * 100)
    print("🚀 PROCESSAMENTO MULTIMODAL - BOOKMARK FOOH")
    print("=" * 100)

    # 1. Buscar bookmark
    print(f"\n📦 1. Buscando bookmark: {FOOH_URL}")
    response = supabase.table("bookmarks").select("*").like("url", f"%{FOOH_URL}%").execute()

    if not response.data:
        print(f"❌ Bookmark não encontrado")
        return

    bookmark = response.data[0]
    bookmark_id = bookmark['id']
    print(f"✅ Bookmark encontrado: {bookmark_id}")
    print(f"   Título: {bookmark.get('title', 'N/A')[:80]}")

    # 2. Baixar vídeo do Supabase Storage
    print(f"\n🎬 2. Baixando vídeo do Supabase Storage...")

    temp_video_path = None
    transcript = ""
    visual_analysis = ""
    language = ""

    try:
        cloud_video_url = bookmark.get('cloud_video_url')

        if cloud_video_url:
            print(f"✅ Cloud URL encontrada: {cloud_video_url[:60]}...")

            # Baixar vídeo temporariamente do Supabase
            import requests
            temp_video_path = f"temp_videos/fooh_{bookmark_id}.mp4"
            os.makedirs("temp_videos", exist_ok=True)

            print(f"📥 Baixando vídeo do Supabase Storage...")
            response = requests.get(cloud_video_url, timeout=120)

            if response.status_code == 200:
                with open(temp_video_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Vídeo baixado: {temp_video_path} ({len(response.content)/1024/1024:.1f}MB)")

                # 3. Análise multimodal do vídeo
                print(f"\n🔬 3. Rodando análise multimodal...")
                print(f"   - Transcrição de áudio (Whisper)")
                print(f"   - Análise visual de frames (GPT-4 Vision)")

                video_analysis = await video_analysis_service.analyze_video(temp_video_path)

                if video_analysis:
                    transcript = video_analysis.get("transcript", "")
                    visual_analysis = video_analysis.get("visual_analysis", "")
                    language = video_analysis.get("language", "")

                    print(f"✅ Análise concluída:")
                    print(f"   - Transcript: {len(transcript)} chars, idioma: {language}")
                    print(f"   - Visual: {len(visual_analysis)} chars")

                    # Mostra preview
                    if transcript:
                        print(f"\n   📝 Transcrição (preview):")
                        print(f"      {transcript[:300]}...")

                    if visual_analysis:
                        print(f"\n   🖼️  Análise Visual:")
                        print(f"      {visual_analysis}")
                else:
                    print(f"⚠️ Análise de vídeo falhou")
            else:
                print(f"❌ Falha ao baixar vídeo: HTTP {response.status_code}")
        else:
            print(f"⚠️ Cloud video URL não encontrada no bookmark")

    except Exception as e:
        print(f"❌ Erro ao baixar/analisar vídeo: {e}")

    # 4. Recapturar metadados com 200 comentários
    print(f"\n📊 4. Recapturando metadados (200 comentários)...")

    metadata_result = await apify_service.extract_metadata(FOOH_URL)

    if metadata_result and hasattr(metadata_result, 'metadata'):
        metadata = metadata_result.metadata or {}
        top_comments = metadata_result.top_comments or []

        print(f"✅ Metadados extraídos:")
        print(f"   - Descrição: {len(metadata.get('description', ''))} chars")
        print(f"   - Hashtags: {len(metadata.get('hashtags', []))}")
        print(f"   - Comentários: {len(top_comments)}")
    else:
        print(f"⚠️ Falha ao extrair metadados")
        metadata = bookmark.get('metadata', {})
        top_comments = []

    # 5. Reprocessar com IA (COM transcript + visual)
    print(f"\n🤖 5. Processando com IA (Claude)...")
    print(f"   Dados disponíveis:")
    print(f"   - Título: ✅")
    print(f"   - Descrição: ✅")
    print(f"   - Hashtags: {len(metadata.get('hashtags', []))}")
    print(f"   - Comentários: {len(top_comments)}")
    print(f"   - Transcrição: {'✅' if transcript else '❌'}")
    print(f"   - Análise Visual: {'✅' if visual_analysis else '❌'}")

    ai_result = await claude_service.process_metadata_auto(
        title=bookmark.get('title', ''),
        description=metadata.get('description', ''),
        hashtags=metadata.get('hashtags', []),
        top_comments=top_comments,
        video_transcript=transcript,
        visual_analysis=visual_analysis
    )

    if ai_result:
        print(f"✅ IA processou com sucesso:")
        print(f"   - Auto Description: {ai_result.get('auto_description', 'N/A')[:100]}...")
        print(f"   - Auto Tags: {', '.join(ai_result.get('auto_tags', []))}")
        print(f"   - Auto Categories: {', '.join(ai_result.get('auto_categories', []))}")
        print(f"   - Confidence: {ai_result.get('confidence', 'N/A')}")

        # Verifica se detectou FOOH
        auto_categories = ai_result.get('auto_categories', [])
        auto_tags = ai_result.get('auto_tags', [])

        fooh_detected = any('FOOH' in str(cat).upper() for cat in auto_categories) or \
                       any('FOOH' in str(tag).upper() for tag in auto_tags)

        if fooh_detected:
            print(f"\n   🎯 ✅ FOOH DETECTADO AUTOMATICAMENTE!")
        else:
            print(f"\n   ⚠️ FOOH NÃO foi detectado automaticamente")
            print(f"      Procurando termos relacionados...")

            all_text = f"{ai_result.get('auto_description', '')} {' '.join(auto_tags)} {' '.join(auto_categories)}"
            fooh_terms = ['cgi', '3d', 'fake', 'augmented', 'ar', 'vfx', 'outdoor']
            found = [term for term in fooh_terms if term in all_text.lower()]

            if found:
                print(f"      Termos encontrados: {', '.join(found)}")
            else:
                print(f"      Nenhum termo relacionado encontrado")
    else:
        print(f"❌ Falha no processamento da IA")
        ai_result = {}

    # 6. Atualizar Supabase
    print(f"\n💾 6. Atualizando Supabase...")

    update_data = {
        'metadata': metadata,
        'auto_description': ai_result.get('auto_description'),
        'auto_tags': ai_result.get('auto_tags', []),
        'auto_categories': ai_result.get('auto_categories', []),
    }

    if transcript:
        update_data['video_transcript'] = transcript
        update_data['transcript_language'] = language

    if visual_analysis:
        update_data['visual_analysis'] = visual_analysis

    try:
        supabase.table("bookmarks").update(update_data).eq("id", bookmark_id).execute()
        print(f"✅ Bookmark atualizado no Supabase")
    except Exception as e:
        print(f"❌ Erro ao atualizar: {e}")

    # 7. Gerar embedding
    print(f"\n🔍 7. Gerando embedding...")

    # Criar texto rico (mesmo que generate_embeddings.py)
    parts = []

    if bookmark.get('title'):
        parts.append(f"Título: {bookmark['title']}")

    if ai_result.get('auto_description'):
        parts.append(f"Descrição: {ai_result['auto_description']}")

    if transcript:
        transcript_limited = transcript[:2000] + "..." if len(transcript) > 2000 else transcript
        parts.append(f"Transcrição (áudio): {transcript_limited}")

    if visual_analysis:
        parts.append(f"Análise Visual: {visual_analysis}")

    all_tags = list(set(ai_result.get('auto_tags', [])))
    if all_tags:
        parts.append(f"Tags: {', '.join(all_tags)}")

    all_categories = list(set(ai_result.get('auto_categories', [])))
    if all_categories:
        parts.append(f"Categorias: {', '.join(all_categories)}")

    if metadata.get('description'):
        parts.append(f"Conteúdo: {metadata['description']}")

    rich_text = "\n".join(parts)
    rich_text = rich_text[:8000] if len(rich_text) > 8000 else rich_text

    print(f"   Texto rico: {len(rich_text)} chars")

    # Gerar embedding com OpenAI
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=rich_text
        )

        embedding = response.data[0].embedding

        # Salvar embedding
        supabase.table("bookmarks").update({
            "embedding": embedding
        }).eq("id", bookmark_id).execute()

        print(f"✅ Embedding gerado e salvo ({len(embedding)} dimensões)")
    except Exception as e:
        print(f"❌ Erro ao gerar embedding: {e}")

    print("\n" + "=" * 100)
    print("✅ PROCESSAMENTO CONCLUÍDO!")
    print("=" * 100)

    print(f"\n📋 RESUMO:")
    print(f"   - Bookmark ID: {bookmark_id}")
    print(f"   - Transcrição: {'✅' if transcript else '❌'}")
    print(f"   - Análise Visual: {'✅' if visual_analysis else '❌'}")
    print(f"   - Comentários: {len(top_comments)}")
    print(f"   - FOOH detectado pela IA: {'✅' if fooh_detected else '❌'}")
    print(f"   - Embedding atualizado: ✅")

    print(f"\n🔍 PRÓXIMO PASSO:")
    print(f"   Testar busca semântica com query 'FOOH' e verificar se esse bookmark aparece!")


if __name__ == "__main__":
    asyncio.run(process_fooh_bookmark())
