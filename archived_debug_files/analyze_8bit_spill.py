"""
Script para executar análise multimodal completa do bookmark "8-Bit Spill"
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Carrega variáveis de ambiente do .env
load_dotenv()

from services.video_analysis_service import video_analysis_service
from services.claude_service import claude_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("SUPABASE_KEY não configurada")

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

async def analyze_8bit_spill():
    """Executa análise multimodal completa do 8-Bit Spill"""

    bookmark_id = "419aa662-420c-4564-81c5-b2138def6b73"
    url = "https://www.instagram.com/reel/DPFquQ9DKc-/?igsh=eHhhYXhxbmdkdTBv"

    logger.info(f"\n{'='*80}")
    logger.info(f"🎬 ANÁLISE MULTIMODAL COMPLETA: 8-Bit Spill")
    logger.info(f"{'='*80}")

    # 1. Busca dados atuais
    logger.info(f"\n📊 ETAPA 1: BUSCANDO DADOS ATUAIS")
    response = supabase.table('bookmarks') \
        .select('*') \
        .eq('id', bookmark_id) \
        .execute()

    if not response.data:
        logger.error(f"❌ Bookmark não encontrado!")
        return

    bookmark = response.data[0]
    metadata = bookmark.get('metadata', {}) or {}

    logger.info(f"✅ Bookmark encontrado: {bookmark.get('title')}")
    logger.info(f"   Views: {metadata.get('views', 0)}")
    logger.info(f"   Likes: {metadata.get('likes', 0)}")
    logger.info(f"   Comentários: {len(metadata.get('top_comments', []))}")

    # Verifica se já tem cloud_video_url
    cloud_video_url = bookmark.get('cloud_video_url')
    local_video_path = bookmark.get('local_video_path')

    logger.info(f"\n📹 Status do vídeo:")
    logger.info(f"   Cloud URL: {'✅ Sim' if cloud_video_url else '❌ Não'}")
    logger.info(f"   Local Path: {'✅ Sim' if local_video_path else '❌ Não'}")

    # 2. Análise multimodal
    logger.info(f"\n{'='*80}")
    logger.info(f"🎤🖼️ ETAPA 2: ANÁLISE MULTIMODAL (Whisper + GPT-4 Vision)")
    logger.info(f"{'='*80}")

    video_path_for_analysis = None

    # Prioriza vídeo local (análise precisa de arquivo no disco)
    if local_video_path:
        # O vídeo foi baixado no CELULAR, mas esse script roda no BACKEND
        # Precisamos que o vídeo esteja no servidor ou baixar temporariamente
        logger.warning(f"⚠️ Vídeo existe no celular, mas não no servidor backend")
        logger.info(f"   Local path (celular): {local_video_path}")
        logger.info(f"   Cloud URL: {cloud_video_url[:80] if cloud_video_url else 'N/A'}...")

        if cloud_video_url:
            logger.info(f"✅ Baixando vídeo temporariamente da cloud...")
            import tempfile
            import requests

            try:
                # Baixa vídeo para arquivo temporário
                response = requests.get(cloud_video_url, stream=True, timeout=60)
                response.raise_for_status()

                # Cria arquivo temporário com extensão .mp4
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')

                # Baixa em chunks
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)

                temp_file.close()
                video_path_for_analysis = temp_file.name

                size_mb = os.path.getsize(video_path_for_analysis) / (1024 * 1024)
                logger.info(f"✅ Vídeo baixado: {video_path_for_analysis} ({size_mb:.2f} MB)")

            except Exception as e:
                logger.error(f"❌ Erro ao baixar vídeo da cloud: {str(e)}")
                video_path_for_analysis = None
    else:
        logger.warning(f"⚠️ Vídeo não disponível localmente")
        logger.info(f"   Para análise completa, é necessário ter o vídeo baixado")
        logger.info(f"   Continuando com análise apenas dos metadados...")

    video_transcript = None
    visual_analysis = None
    transcript_language = None

    if video_path_for_analysis:
        try:
            logger.info(f"🎬 Iniciando análise do vídeo...")

            # Chama serviço de análise multimodal
            analysis_result = await video_analysis_service.analyze_video(
                video_path=video_path_for_analysis
            )

            if analysis_result:
                video_transcript = analysis_result.get('transcript')
                visual_analysis = analysis_result.get('visual_analysis')
                transcript_language = analysis_result.get('language')

                logger.info(f"\n✅ ANÁLISE MULTIMODAL CONCLUÍDA:")
                logger.info(f"   🎤 Transcrição: {'✅ Sim' if video_transcript else '❌ Não'} ({len(video_transcript) if video_transcript else 0} chars)")
                logger.info(f"   🖼️ Análise Visual: {'✅ Sim' if visual_analysis else '❌ Não'} ({len(visual_analysis) if visual_analysis else 0} chars)")
                logger.info(f"   🌐 Idioma: {transcript_language or 'N/A'}")

                if video_transcript:
                    logger.info(f"\n📝 TRANSCRIÇÃO:")
                    logger.info(f"   {video_transcript[:200]}...")

                if visual_analysis:
                    logger.info(f"\n🖼️ ANÁLISE VISUAL:")
                    logger.info(f"   {visual_analysis[:200]}...")

                # Salva no Supabase
                update_data = {
                    'video_transcript': video_transcript,
                    'visual_analysis': visual_analysis,
                    'transcript_language': transcript_language,
                    'analyzed_at': 'now()'
                }
                supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()
                logger.info(f"\n💾 Análise multimodal salva no Supabase!")

            else:
                logger.error(f"❌ Análise multimodal falhou (sem resultado)")

        except Exception as e:
            logger.error(f"❌ Erro na análise multimodal: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        logger.info(f"⚠️ Pulando análise multimodal (vídeo não disponível)")

    # 3. Reprocessa com IA incluindo transcrição e análise visual
    logger.info(f"\n{'='*80}")
    logger.info(f"🤖 ETAPA 3: REPROCESSAMENTO COM IA (com transcrição + visual)")
    logger.info(f"{'='*80}")

    try:
        result = await claude_service.process_metadata_auto(
            title=bookmark.get('title'),
            description=metadata.get('description', ''),
            hashtags=metadata.get('hashtags', []),
            top_comments=metadata.get('top_comments', []),
            video_transcript=video_transcript or bookmark.get('video_transcript', ''),
            visual_analysis=visual_analysis or bookmark.get('visual_analysis', ''),
            user_context=bookmark.get('user_context_raw', '')
        )

        if result:
            # Salva resultados da IA (INCLUINDO filtered_comments!)
            update_data = {
                'auto_description': result.get('auto_description'),
                'auto_tags': result.get('auto_tags'),
                'auto_categories': result.get('auto_categories'),
                'relevance_score': result.get('relevance_score'),
                'ai_processed': True
            }

            # ⭐ FILTERED_COMMENTS (TOP 5)
            if 'filtered_comments' in result:
                update_data['filtered_comments'] = result['filtered_comments']
                logger.info(f"\n💬 TOP 5 COMENTÁRIOS FILTRADOS:")
                for i, comment in enumerate(result['filtered_comments'][:5], 1):
                    logger.info(f"   {i}. {comment.get('text', '')[:80]}...")

            supabase.table('bookmarks').update(update_data).eq('id', bookmark_id).execute()

            logger.info(f"\n✅ SUCESSO! DADOS COMPLETOS SALVOS:")
            logger.info(f"   📝 auto_description: {result.get('auto_description')[:100]}...")
            logger.info(f"   🏷️ auto_tags: {result.get('auto_tags')}")
            logger.info(f"   📁 auto_categories: {result.get('auto_categories')}")
            logger.info(f"   ⭐ relevance_score: {result.get('relevance_score')}")
            logger.info(f"   💬 filtered_comments: {len(result.get('filtered_comments', []))} comentários")
        else:
            logger.error(f"❌ Processamento de IA falhou")

    except Exception as e:
        logger.error(f"❌ Erro no reprocessamento: {str(e)}")
        import traceback
        traceback.print_exc()

    logger.info(f"\n{'='*80}")
    logger.info(f"✅ ANÁLISE COMPLETA CONCLUÍDA!")
    logger.info(f"{'='*80}")
    logger.info(f"\n📱 No app, faça pull-to-refresh para ver os novos dados:")
    logger.info(f"   - 🎤 Transcrição do áudio")
    logger.info(f"   - 🖼️ Análise visual dos frames")
    logger.info(f"   - 💬 Top 5 comentários filtrados")

    # Cleanup: remove arquivo temporário
    if video_path_for_analysis and video_path_for_analysis.startswith('/tmp'):
        try:
            os.unlink(video_path_for_analysis)
            logger.info(f"\n🧹 Arquivo temporário removido: {video_path_for_analysis}")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível remover arquivo temporário: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_8bit_spill())
