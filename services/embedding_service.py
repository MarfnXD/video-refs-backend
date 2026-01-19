"""
Serviço para geração de embeddings usando Gemini Embedding API

Embeddings são vetores de 768 dimensões que capturam significado semântico.
Usado para:
- Clusterização visual (UMAP 768D → 2D)
- Busca por similaridade
- Recomendações

Modelo: text-embedding-004 (estável, 768 dimensões)
Custo: ~$0.00001 por embedding (praticamente grátis)
"""
import os
import logging
from typing import Optional, List
import google.generativeai as genai

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY não configurada - Embedding service desabilitado")
            self.client = None
        else:
            genai.configure(api_key=api_key)
            self.client = genai

        # Modelo de embedding (768 dimensões)
        self.model_name = "models/text-embedding-004"

    def generate_embedding(
        self,
        smart_title: Optional[str] = None,
        auto_tags: Optional[List[str]] = None,
        auto_categories: Optional[List[str]] = None,
        video_transcript: Optional[str] = None,
        visual_analysis: Optional[str] = None
    ) -> Optional[List[float]]:
        """
        Gera embedding combinando múltiplos campos do bookmark

        Prioridade de informação:
        1. smart_title (40%) - Título descritivo gerado pela IA
        2. auto_tags (20%) - Tags automáticas
        3. auto_categories (10%) - Categorias
        4. video_transcript (15%) - Transcrição de áudio
        5. visual_analysis (15%) - Análise visual

        Args:
            smart_title: Título descritivo (ex: "Tutorial de Motion Graphics com After Effects")
            auto_tags: Lista de tags (ex: ["motion design", "after effects"])
            auto_categories: Lista de categorias (ex: ["Tutorial", "Motion Design"])
            video_transcript: Transcrição do áudio/legendas
            visual_analysis: Análise visual do Gemini Flash

        Returns:
            Lista de 768 floats ou None se falhar
        """
        if not self.client:
            logger.error("❌ Embedding client não inicializado (GEMINI_API_KEY faltando)")
            return None

        try:
            # Montar texto combinado (priorizando campos mais importantes)
            text_parts = []

            # 1. Smart title (repetido 2x para dar mais peso)
            if smart_title:
                text_parts.append(smart_title)
                text_parts.append(smart_title)

            # 2. Tags (separadas por vírgula)
            if auto_tags:
                text_parts.append(", ".join(auto_tags))

            # 3. Categorias
            if auto_categories:
                text_parts.append(", ".join(auto_categories))

            # 4. Transcrição (primeiros 500 caracteres)
            if video_transcript:
                text_parts.append(video_transcript[:500])

            # 5. Análise visual (primeiros 500 caracteres)
            if visual_analysis:
                text_parts.append(str(visual_analysis)[:500])

            # Combinar tudo
            combined_text = " | ".join(filter(None, text_parts))

            if not combined_text:
                logger.warning("⚠️ Nenhum conteúdo para gerar embedding")
                return None

            logger.info(f"📊 Gerando embedding - Texto combinado: {len(combined_text)} chars")
            logger.debug(f"Preview: {combined_text[:200]}...")

            # Chamar API do Gemini
            result = genai.embed_content(
                model=self.model_name,
                content=combined_text,
                task_type="clustering"  # Otimizado para clusterização
            )

            # Extrair embedding
            embedding = result['embedding']

            logger.info(f"✅ Embedding gerado - Dimensões: {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"❌ Erro ao gerar embedding: {str(e)}")
            return None

    def generate_from_bookmark_dict(self, bookmark: dict) -> Optional[List[float]]:
        """
        Helper para gerar embedding a partir de dict do Supabase

        Args:
            bookmark: Dict com campos do bookmark (smart_title, auto_tags, etc)

        Returns:
            Lista de 768 floats ou None
        """
        return self.generate_embedding(
            smart_title=bookmark.get('smart_title'),
            auto_tags=bookmark.get('auto_tags'),
            auto_categories=bookmark.get('auto_categories'),
            video_transcript=bookmark.get('video_transcript'),
            visual_analysis=bookmark.get('visual_analysis')
        )


# Singleton instance
embedding_service = EmbeddingService()
