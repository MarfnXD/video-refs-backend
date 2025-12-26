#!/usr/bin/env python3
"""
Exporta resultados completos dos bookmarks processados para análise de qualidade.
Mostra TODAS as etapas: Metadata → Gemini 2.5 Flash → Gemini 3.0 Pro
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializar Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def export_quality_report(limit: int = 5):
    """Exporta relatório de qualidade dos últimos N bookmarks processados"""

    print("📊 Consultando bookmarks processados...")

    try:
        # Buscar últimos N bookmarks processados (ordenar por created_at DESC)
        result = supabase.table('bookmarks').select('*').order('created_at', desc=True).limit(limit).execute()

        if not result.data or len(result.data) == 0:
            print("❌ Nenhum bookmark encontrado")
            return

        bookmarks = result.data
        print(f"✓ {len(bookmarks)} bookmarks encontrados\n")

        # Gerar relatório em Markdown
        report_lines = []
        report_lines.append("# 📊 RELATÓRIO DE QUALIDADE - PROCESSAMENTO DE VÍDEOS\n")
        report_lines.append(f"**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        report_lines.append(f"**Total de vídeos**: {len(bookmarks)}\n")
        report_lines.append("---\n\n")

        for idx, bookmark in enumerate(bookmarks, 1):
            report_lines.append(f"## 🎬 VÍDEO {idx}/{len(bookmarks)}\n")
            report_lines.append(f"**ID**: `{bookmark.get('id', 'N/A')}`\n")
            report_lines.append(f"**URL**: {bookmark.get('url', 'N/A')}\n")
            report_lines.append(f"**Status**: `{bookmark.get('processing_status', 'N/A')}`\n")
            report_lines.append(f"**Criado em**: {bookmark.get('created_at', 'N/A')}\n")

            if bookmark.get('error_message'):
                report_lines.append(f"**⚠️ Erro**: {bookmark.get('error_message')}\n")

            report_lines.append("\n---\n\n")

            # ETAPA 1: METADADOS (Apify)
            report_lines.append("### 📊 ETAPA 1: EXTRAÇÃO DE METADADOS (Apify)\n")

            metadata = bookmark.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            if metadata:
                report_lines.append(f"**✅ Status**: Metadados extraídos com sucesso\n\n")
                report_lines.append(f"- **Título**: {metadata.get('title', 'N/A')}\n")
                report_lines.append(f"- **Plataforma**: {bookmark.get('platform', 'N/A')}\n")
                report_lines.append(f"- **Descrição**: {metadata.get('description', 'N/A')[:200]}{'...' if len(metadata.get('description', '')) > 200 else ''}\n")
                report_lines.append(f"- **Autor**: {metadata.get('author', 'N/A')}\n")
                report_lines.append(f"- **Views**: {metadata.get('views', 'N/A'):,}\n" if metadata.get('views') else "- **Views**: N/A\n")
                report_lines.append(f"- **Likes**: {metadata.get('likes', 'N/A'):,}\n" if metadata.get('likes') else "- **Likes**: N/A\n")
                report_lines.append(f"- **Comentários**: {metadata.get('comments_count', 'N/A'):,}\n" if metadata.get('comments_count') else "- **Comentários**: N/A\n")
                report_lines.append(f"- **Duração**: {metadata.get('duration', 'N/A')}\n")
                report_lines.append(f"- **Publicado em**: {metadata.get('published_at', 'N/A')}\n")

                # Hashtags
                hashtags = metadata.get('hashtags', [])
                if hashtags:
                    report_lines.append(f"- **Hashtags**: {', '.join(['#' + tag for tag in hashtags[:10]])}\n")

                # Top comentários (ordenados por likes)
                top_comments = metadata.get('top_comments', [])
                if top_comments and len(top_comments) > 0:
                    # Ordenar por likes (mais relevantes primeiro)
                    sorted_comments = sorted(
                        top_comments,
                        key=lambda x: x.get('likes', 0) if isinstance(x, dict) else 0,
                        reverse=True
                    )

                    report_lines.append(f"\n**Top 3 Comentários (por likes)**:\n")
                    for i, comment in enumerate(sorted_comments[:3], 1):
                        text = comment.get('text', '') if isinstance(comment, dict) else str(comment)
                        likes = comment.get('likes', 0) if isinstance(comment, dict) else 0
                        report_lines.append(f"{i}. \"{text[:100]}{'...' if len(text) > 100 else ''}\" ({likes:,} likes)\n")
            else:
                report_lines.append("**❌ Status**: Metadados não extraídos\n")

            report_lines.append("\n---\n\n")

            # ETAPA 2: ANÁLISE VISUAL (Gemini 2.5 Flash)
            report_lines.append("### 🎬 ETAPA 2: ANÁLISE VISUAL E ÁUDIO (Gemini 2.5 Flash)\n")

            video_transcript = bookmark.get('video_transcript', '')
            visual_analysis = bookmark.get('visual_analysis', '')
            audio_analysis = bookmark.get('audio_analysis', '')
            editing_techniques = bookmark.get('editing_techniques', '')
            storytelling_elements = bookmark.get('storytelling_elements', '')
            is_fooh = bookmark.get('is_fooh', False)
            detected_language = bookmark.get('detected_language', '')

            if video_transcript or visual_analysis:
                report_lines.append(f"**✅ Status**: Análise multimodal concluída\n\n")

                if detected_language:
                    report_lines.append(f"- **Idioma detectado**: {detected_language}\n")

                report_lines.append(f"- **FOOH (Fake Out of Home)**: {'Sim' if is_fooh else 'Não'}\n")

                if video_transcript:
                    report_lines.append(f"\n**📝 Transcrição de Áudio** ({len(video_transcript)} caracteres):\n")
                    report_lines.append(f"```\n{video_transcript}\n```\n")

                # ✅ Só mostrar visual_analysis se for DIFERENTE de transcript (evitar duplicação)
                if visual_analysis and visual_analysis != video_transcript:
                    report_lines.append(f"\n**👁️ Análise Visual** ({len(visual_analysis)} caracteres):\n")
                    report_lines.append(f"{visual_analysis}\n")

                if audio_analysis:
                    report_lines.append(f"\n**🔊 Análise de Áudio**:\n")
                    report_lines.append(f"{audio_analysis[:300]}{'...' if len(audio_analysis) > 300 else ''}\n")

                if editing_techniques:
                    report_lines.append(f"\n**✂️ Técnicas de Edição**:\n")
                    report_lines.append(f"{editing_techniques[:300]}{'...' if len(editing_techniques) > 300 else ''}\n")

                if storytelling_elements:
                    report_lines.append(f"\n**📖 Elementos de Storytelling**:\n")
                    report_lines.append(f"{storytelling_elements[:300]}{'...' if len(storytelling_elements) > 300 else ''}\n")
            else:
                report_lines.append("**❌ Status**: Análise visual não realizada\n")

            report_lines.append("\n---\n\n")

            # ETAPA 3: PROCESSAMENTO FINAL (Gemini 3.0 Pro)
            report_lines.append("### 🤖 ETAPA 3: PROCESSAMENTO FINAL (Gemini 3.0 Pro)\n")

            auto_tags = bookmark.get('auto_tags', [])
            auto_categories = bookmark.get('auto_categories', [])
            auto_description = bookmark.get('auto_description', '')
            relevance_score = bookmark.get('relevance_score', 0)
            ai_processed = bookmark.get('ai_processed', False)

            if ai_processed:
                report_lines.append(f"**✅ Status**: Processamento de IA concluído\n\n")

                report_lines.append(f"- **Score de Relevância**: {relevance_score:.2f}/1.00\n")

                if auto_description:
                    report_lines.append(f"\n**📝 Descrição Automática**:\n")
                    report_lines.append(f"{auto_description}\n")

                if auto_tags:
                    report_lines.append(f"\n**🏷️ Tags Automáticas** ({len(auto_tags)} tags):\n")
                    report_lines.append(f"{', '.join(['`' + tag + '`' for tag in auto_tags])}\n")

                if auto_categories:
                    report_lines.append(f"\n**📁 Categorias Automáticas** ({len(auto_categories)} categorias):\n")
                    report_lines.append(f"{', '.join(['`' + cat + '`' for cat in auto_categories])}\n")
            else:
                report_lines.append("**❌ Status**: Processamento de IA não realizado\n")

            report_lines.append("\n---\n\n")

            # RESUMO FINAL
            report_lines.append("### 📋 RESUMO FINAL\n")
            report_lines.append(f"- **Metadados extraídos**: {'✅ Sim' if metadata else '❌ Não'}\n")
            report_lines.append(f"- **Análise visual**: {'✅ Sim' if (video_transcript or visual_analysis) else '❌ Não'}\n")
            report_lines.append(f"- **IA processou**: {'✅ Sim' if ai_processed else '❌ Não'}\n")
            report_lines.append(f"- **Tags geradas**: {len(auto_tags) if auto_tags else 0}\n")
            report_lines.append(f"- **Categorias geradas**: {len(auto_categories) if auto_categories else 0}\n")
            report_lines.append(f"- **Status final**: `{bookmark.get('processing_status', 'N/A')}`\n")

            report_lines.append("\n" + "="*80 + "\n\n")

        # Salvar arquivo
        filename = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(report_lines)

        print(f"✅ Relatório gerado: {filename}")
        print(f"\n📄 Total de linhas: {len(report_lines)}")
        print(f"📊 Arquivo pode ser aberto em qualquer editor Markdown\n")

        return filename

    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    export_quality_report(limit=5)
