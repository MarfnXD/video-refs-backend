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

    async def process_metadata_auto(
        self,
        title: str,
        description: str = "",
        hashtags: List[str] = None,
        top_comments: List[Dict] = None,
        video_transcript: str = "",
        visual_analysis: str = "",
        user_context: str = ""
    ) -> Optional[Dict]:
        """
        Processa metadados do vídeo automaticamente (com ou sem contexto do usuário)

        Args:
            title: Título do vídeo
            description: Descrição do vídeo
            hashtags: Lista de hashtags
            top_comments: Lista de comentários top [{text, likes, author}]
            video_transcript: Transcrição do áudio (Whisper API)
            visual_analysis: Análise visual dos frames (GPT-4 Vision)
            user_context: Contexto manual do usuário (opcional - peso máximo se fornecido)

        Returns:
            Dict com auto_description, auto_tags, auto_categories
        """
        if not self.client:
            logger.error("Claude client não inicializado (REPLICATE_API_TOKEN faltando)")
            return None

        try:
            logger.info(f"🤖 Processando metadados automaticamente com Claude...")

            # DEBUG: Log dos parâmetros recebidos
            logger.debug(f"📊 Parâmetros recebidos:")
            logger.debug(f"   title: {len(title)} chars")
            logger.debug(f"   visual_analysis: {len(visual_analysis) if visual_analysis else 0} chars")
            logger.debug(f"   user_context: {len(user_context) if user_context else 0} chars")
            if visual_analysis:
                logger.debug(f"   visual_analysis preview: {visual_analysis[:200]}...")

            # Preparar dados
            hashtags_str = ", ".join(hashtags) if hashtags else "Nenhuma"

            # Filtrar e formatar comentários (guardamos os filtrados para retornar)
            filtered_comments_list = []
            if top_comments:
                filtered_comments_list = self._filter_and_prioritize_comments(top_comments, max_count=50)
                comments_str = self._format_filtered_comments(filtered_comments_list)
            else:
                comments_str = "Nenhum"

            # Montar prompt (com transcrição, análise visual e contexto do usuário)
            prompt = self._build_auto_prompt(
                title, description, hashtags_str, comments_str,
                video_transcript, visual_analysis, user_context
            )

            # Chamar Claude via Replicate
            output = self.client.run(
                "anthropic/claude-3.5-sonnet",
                input={
                    "prompt": prompt,
                    "max_tokens": 1024,
                    "temperature": 0.2,  # Mais determinístico para análise automática
                    "top_p": 0.9
                }
            )

            # Extrair resposta
            response_text = ""
            for chunk in output:
                response_text += chunk

            logger.debug(f"Resposta Claude (auto): {response_text}")

            # Parse JSON
            result = json.loads(response_text)

            # Adicionar comentários filtrados ao resultado
            result['filtered_comments'] = filtered_comments_list

            logger.info(f"✅ Processamento automático concluído: {len(result.get('auto_tags', []))} tags, {len(filtered_comments_list)} comentários filtrados")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao parsear JSON da resposta Claude (auto): {str(e)}")
            logger.error(f"Resposta raw: {response_text}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao processar metadados automaticamente: {str(e)}")
            return None

    def _is_generic_comment(self, text: str) -> bool:
        """Detecta comentários genéricos/irrelevantes"""
        if not text or len(text.strip()) < 3:
            return True

        text_lower = text.lower().strip()

        # Lista de padrões genéricos (português + inglês + espanhol)
        generic_patterns = [
            # Português
            "top", "kkk", "kkkk", "primeiro", "segunda", "primeirão",
            "like", "mt bom", "demais", "foda", "incrivel", "show",
            # Inglês
            "first", "second", "nice", "cool", "wow", "great", "amazing",
            "love it", "love this", "awesome", "fire", "lit",
            # Espanhol
            "primero", "que bueno", "increible",
            # Emojis/símbolos comuns
            "❤", "🔥", "😍", "👏", "💯", "😂", "🤣", "👍",
        ]

        # Verifica se é APENAS emojis ou APENAS uma palavra genérica
        for pattern in generic_patterns:
            if text_lower == pattern or text_lower.replace(" ", "") == pattern.replace(" ", ""):
                return True

        # Se tem menos de 5 caracteres e contém emojis, provavelmente é genérico
        if len(text_lower) < 5 and any(char in text for char in "❤🔥😍👏💯😂🤣👍"):
            return True

        return False

    def _filter_and_prioritize_comments(self, comments: List[Dict], max_count: int = 50) -> List[Dict]:
        """Filtra comentários genéricos e prioriza por relevância"""
        if not comments:
            return []

        # Filtrar comentários genéricos
        filtered = [c for c in comments if not self._is_generic_comment(c.get('text', ''))]

        # Se filtrou tudo, usa os originais (melhor comentários genéricos que nenhum)
        if not filtered:
            filtered = comments

        # Ordenar por likes (comentários com mais likes primeiro)
        sorted_comments = sorted(filtered, key=lambda x: x.get('likes', 0), reverse=True)

        # Retornar os top N
        return sorted_comments[:max_count]

    def _format_filtered_comments(self, filtered_comments: List[Dict]) -> str:
        """Formata comentários já filtrados para o prompt"""
        if not filtered_comments:
            return "Nenhum comentário relevante"

        formatted = []
        for i, comment in enumerate(filtered_comments, 1):
            text = comment.get('text', '')
            likes = comment.get('likes', 0)
            formatted.append(f"  {i}. \"{text}\" ({likes} likes)")

        return "\n".join(formatted)

    def _format_comments(self, comments: List[Dict]) -> str:
        """Formata comentários para o prompt (com filtro inteligente)"""
        if not comments:
            return "Nenhum"

        # Filtrar e priorizar (50 melhores comentários)
        filtered_comments = self._filter_and_prioritize_comments(comments, max_count=50)

        if not filtered_comments:
            return "Nenhum comentário relevante"

        formatted = []
        for i, comment in enumerate(filtered_comments, 1):
            text = comment.get('text', '')
            likes = comment.get('likes', 0)
            formatted.append(f"  {i}. \"{text}\" ({likes} likes)")

        return "\n".join(formatted)

    def _build_auto_prompt(
        self,
        title: str,
        description: str,
        hashtags_str: str,
        comments_str: str,
        video_transcript: str = "",
        visual_analysis: str = "",
        user_context: str = ""
    ) -> str:
        """Constrói o prompt para processamento automático de metadados"""
        return f"""Você é um assistente que extrai tags e categorias de vídeos de referência criativa.

DADOS DISPONÍVEIS (em ordem de confiabilidade):

🎬 ANÁLISE VISUAL DO VÍDEO (Gemini Flash 2.5 - FONTE PRIMÁRIA):
{visual_analysis if visual_analysis else 'Não disponível'}
⚠️ Esta é a VERDADE ABSOLUTA - o Gemini VIU o vídeo completo e descreveu objetivamente.

👤 CONTEXTO DO USUÁRIO (2ª prioridade - se fornecido):
{user_context if user_context else 'Não fornecido'}
⚠️ Se fornecido, o usuário sabe POR QUE salvou - considere fortemente na análise.

📊 METADADOS EXTERNOS (Apify - VALIDAR CRITICAMENTE):
- Título: "{title}"
- Descrição: "{description or 'Não disponível'}"
- Hashtags: {hashtags_str}
- Comentários: {comments_str}

⚠️ IMPORTANTE: Estes metadados podem estar ERRADOS ou ser CLICKBAIT.
Você DEVE validar se fazem sentido com o que o Gemini descreveu.

INSTRUÇÕES DE VALIDAÇÃO:

1. **Comece pela análise do Gemini** - ela é a fonte primária de verdade
2. **Se houver contexto do usuário**, considere fortemente (ele sabe por que salvou)
3. **Valide os metadados Apify criticamente**:
   - O título/descrição BATE com o que o Gemini descreveu?
   - Os comentários fazem sentido com a análise visual?
   - As hashtags são relevantes ou apenas spam/clickbait?
4. **IGNORE dados que contradizem o Gemini**:
   - Exemplo: Gemini diz "animação 3D de Monsters Inc" mas título diz "marketing com AI"
   - Neste caso: IGNORE o título, baseie-se NO QUE REALMENTE ESTÁ NO VÍDEO
5. **Use apenas dados que AGREGAM à análise do Gemini**:
   - Se título/comentários adicionam contexto útil → use
   - Se são genéricos/contraditórios/clickbait → ignore

REGRAS DE EXTRAÇÃO:

- Tags devem refletir o que o Gemini VIU (não o que título/comentários dizem)
- Se Gemini menciona "animação 3D" → tag: "3d-animation"
- Se Gemini menciona técnica específica (jump cut, slow motion) → tag com a técnica
- Categorias devem fazer sentido com CONTEÚDO REAL do vídeo
- NÃO force FOOH/CGI se Gemini não mencionar explicitamente outdoor/billboard CGI

HIERARQUIA FINAL (ordem de prioridade):

1️⃣ Análise Visual Gemini = VERDADE ABSOLUTA (ele VIU o vídeo!)
2️⃣ Contexto do usuário = 2ª prioridade (se fornecido)
3️⃣ Metadados Apify = Use APENAS se validarem com Gemini

CATEGORIAS DISPONÍVEIS:
- Técnica de Edição
- Referência Visual
- Ideia de Conteúdo
- Áudio/Música
- Ferramenta/Software
- Mecânica de Campanha
- Storytelling
- Tutorial
- Case de Sucesso
- FOOH / CGI Advertising (APENAS se Gemini mencionar outdoor/billboard CGI em ambiente real)
- Outro

RETORNE APENAS JSON:
{{
  "auto_description": "string (baseado PRINCIPALMENTE na análise Gemini)",
  "auto_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "auto_categories": ["categoria1", "categoria2"],
  "confidence": "high|medium|low",
  "relevance_score": 0.0-1.0
}}"""

    async def process_metadata_with_gemini(
        self,
        title: str,
        description: str = "",
        hashtags: List[str] = None,
        top_comments: List[Dict] = None,
        gemini_analysis: Dict = None,
        user_context: str = ""
    ) -> Optional[Dict]:
        """
        **ATUALIZADO - GEMINI FLASH 2.5 TIMELINE FORMAT**

        Processa metadados do vídeo usando descrição timeline do Gemini Flash 2.5

        Args:
            title: Título do vídeo
            description: Descrição do vídeo
            hashtags: Lista de hashtags
            top_comments: Lista de comentários top [{text, likes, author}]
            gemini_analysis: Dict retornado pelo Gemini (formato novo):
                - transcript: Descrição timeline objetiva do vídeo
                - visual_analysis: Mesmo conteúdo (compatibilidade)
                - language: Idioma detectado
                - confidence: 0.0-1.0
            user_context: Contexto manual do usuário (opcional - peso máximo)

        Returns:
            Dict com auto_description, auto_tags, auto_categories, relevance_score
        """
        if not self.client:
            logger.error("❌ Claude client não inicializado (REPLICATE_API_TOKEN faltando)")
            return None

        try:
            logger.info(f"🤖 Processando metadados com Gemini timeline...")

            # DEBUG: Log gemini_analysis recebido
            if gemini_analysis:
                logger.debug(f"📊 Gemini analysis recebido: {list(gemini_analysis.keys())}")
                logger.debug(f"   transcript: {len(gemini_analysis.get('transcript', ''))} chars")
                logger.debug(f"   visual_analysis: {len(gemini_analysis.get('visual_analysis', ''))} chars")
            else:
                logger.warning(f"⚠️ gemini_analysis é None!")

            # Preparar dados
            hashtags_str = ", ".join(hashtags) if hashtags else "Nenhuma"

            # Filtrar comentários
            filtered_comments_list = []
            if top_comments:
                filtered_comments_list = self._filter_and_prioritize_comments(top_comments, max_count=50)
                comments_str = self._format_filtered_comments(filtered_comments_list)
            else:
                comments_str = "Nenhum"

            # Extrair descrição timeline do Gemini (formato novo - texto livre)
            gemini_timeline = gemini_analysis.get('visual_analysis', '') if gemini_analysis else ''

            # DEBUG: Log do timeline extraído
            logger.debug(f"📝 Timeline extraído: {len(gemini_timeline)} chars")
            if gemini_timeline:
                logger.debug(f"   Preview: {gemini_timeline[:200]}...")

            # Usar método process_metadata_auto (que já foi atualizado)
            # passando a descrição do Gemini como visual_analysis
            return await self.process_metadata_auto(
                title=title,
                description=description,
                hashtags=hashtags,
                top_comments=top_comments,
                video_transcript="",  # Gemini já inclui áudio na timeline
                visual_analysis=gemini_timeline,
                user_context=user_context
            )

        except Exception as e:
            logger.error(f"❌ Erro ao processar metadados com Gemini: {str(e)}")
            return None

    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return self.client is not None

# Instância global do serviço
claude_service = ClaudeService()