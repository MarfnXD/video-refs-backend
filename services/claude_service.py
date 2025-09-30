"""
Serviço para processamento de contexto usando Claude 3.5 Sonnet via Replicate
"""
import os
import json
import replicate
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self):
        api_token = os.getenv("REPLICATE_API_TOKEN")
        if not api_token:
            logger.warning("REPLICATE_API_TOKEN não configurada")
            self.client = None
        else:
            self.client = replicate.Client(api_token=api_token)

    async def process_context(
        self,
        user_context_raw: str,
        video_title: str = "",
        platform: str = "",
        author: str = "",
        user_categories: List[str] = None,
        user_projects: List[str] = None
    ) -> Optional[Dict]:
        """
        Processa contexto do usuário com Claude 3.5 Sonnet

        Args:
            user_context_raw: Contexto original do usuário
            video_title: Título do vídeo
            platform: Plataforma (YouTube, Instagram, TikTok)
            author: Autor/canal do vídeo
            user_categories: Categorias existentes do usuário
            user_projects: Projetos existentes do usuário

        Returns:
            Dict com contexto processado, tags, categorias e projetos sugeridos
        """
        if not self.client:
            logger.error("Claude client não inicializado (REPLICATE_API_TOKEN faltando)")
            return None

        if not user_context_raw or not user_context_raw.strip():
            logger.warning("Contexto vazio, pulando processamento")
            return None

        try:
            logger.info(f"🧠 Processando contexto com Claude via Replicate...")

            # Preparar listas para o prompt
            categories_list = ", ".join(user_categories) if user_categories else "Nenhuma categoria ainda"
            projects_list = ", ".join(user_projects) if user_projects else "Nenhum projeto ainda"

            # Montar prompt
            prompt = self._build_prompt(
                user_context_raw,
                video_title,
                platform,
                author,
                categories_list,
                projects_list
            )

            # Chamar Claude via Replicate
            # https://replicate.com/anthropic/claude-3.5-sonnet
            output = self.client.run(
                "anthropic/claude-3.5-sonnet",
                input={
                    "prompt": prompt,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            )

            # Extrair resposta (output é um iterator de strings)
            response_text = ""
            for chunk in output:
                response_text += chunk

            logger.debug(f"Resposta Claude: {response_text}")

            # Parse JSON
            result = json.loads(response_text)

            logger.info(f"✅ Processamento concluído: {len(result.get('tags', []))} tags, {len(result.get('suggested_categories', []))} categorias")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao parsear JSON da resposta Claude: {str(e)}")
            logger.error(f"Resposta raw: {response_text}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao processar contexto com Claude: {str(e)}")
            return None

    def _build_prompt(
        self,
        user_context: str,
        video_title: str,
        platform: str,
        author: str,
        categories_list: str,
        projects_list: str
    ) -> str:
        """Constrói o prompt para Claude"""
        return f"""Você é um assistente especializado em organizar referências criativas para profissionais de vídeo/marketing.

CONTEXTO DO USUÁRIO:
"{user_context}"

METADADOS DO VÍDEO:
- Título: {video_title or "N/A"}
- Plataforma: {platform or "N/A"}
- Canal/Autor: {author or "N/A"}

CATEGORIAS EXISTENTES DO USUÁRIO:
{categories_list}

PROJETOS EXISTENTES DO USUÁRIO:
{projects_list}

TAREFA:
1. Melhore a nota do usuário (mantenha o sentido, mas torne mais claro e estruturado)
2. Extraia tags relevantes (máximo 5)
3. Sugira MÚLTIPLAS categorias (1-3) dentre as padrões ou crie novas:
   PADRÕES:
   - Ideia de Conteúdo
   - Técnica de Edição
   - Referência Visual
   - Áudio/Música
   - Mecânica de Campanha
   - Ferramenta/Software
   - Storytelling
   - Outro

   Se o contexto mencionar algo específico não coberto, sugira nova categoria.
   Priorize categorias que o usuário já usa (se aplicável).

4. Extraia projetos mencionados ou sugira projetos existentes relevantes (máximo 2)
   - Se usuário menciona "para cliente X", "campanha Y", extraia como projeto
   - Se contexto é similar a projetos existentes, sugira

5. Identifique palavras-chave para busca futura

RETORNE APENAS JSON (sem markdown, sem explicações):
{{
  "context_processed": "string (contexto melhorado)",
  "tags": ["tag1", "tag2"],
  "suggested_categories": ["categoria1", "categoria2"],
  "suggested_projects": ["projeto1"],
  "search_keywords": ["keyword1", "keyword2"],
  "confidence": "high|medium|low (quão confiante nas sugestões)"
}}"""

    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return self.client is not None

# Instância global do serviço
claude_service = ClaudeService()