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
        top_comments: List[Dict] = None
    ) -> Optional[Dict]:
        """
        Processa metadados do vídeo automaticamente (sem contexto do usuário)

        Args:
            title: Título do vídeo
            description: Descrição do vídeo
            hashtags: Lista de hashtags
            top_comments: Lista de comentários top [{text, likes, author}]

        Returns:
            Dict com auto_description, auto_tags, auto_categories
        """
        if not self.client:
            logger.error("Claude client não inicializado (REPLICATE_API_TOKEN faltando)")
            return None

        try:
            logger.info(f"🤖 Processando metadados automaticamente com Claude...")

            # Preparar dados
            hashtags_str = ", ".join(hashtags) if hashtags else "Nenhuma"
            comments_str = self._format_comments(top_comments) if top_comments else "Nenhum"

            # Montar prompt
            prompt = self._build_auto_prompt(title, description, hashtags_str, comments_str)

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

            logger.info(f"✅ Processamento automático concluído: {len(result.get('auto_tags', []))} tags")
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
        comments_str: str
    ) -> str:
        """Constrói o prompt para processamento automático de metadados"""
        return f"""Você é um assistente especializado em analisar vídeos de referência criativa.

ANALISE OS METADADOS ABAIXO E EXTRAIA INFORMAÇÕES RELEVANTES:

📌 TÍTULO (peso 35%): "{title}"

📄 DESCRIÇÃO (peso 30%):
"{description or 'Não disponível'}"

#️⃣ HASHTAGS (peso 20%):
{hashtags_str}

💬 COMENTÁRIOS TOP FILTRADOS (peso 15%):
{comments_str}
(Comentários genéricos já foram filtrados automaticamente. Estes são os mais relevantes ordenados por likes.)

INSTRUÇÕES DE ANÁLISE:
1. **Validação de Consistência**:
   - Se o título NÃO se relaciona com a descrição, reduza o peso do título
   - Se título for genérico tipo "😱", "TRENDING", priorize descrição/hashtags

2. **Análise de Comentários**:
   - Os comentários JÁ FORAM FILTRADOS (removidos genéricos como "top", "🔥", etc)
   - Dê MAIS PESO aos comentários - eles revelam como pessoas descrevem o vídeo
   - Comentários podem conter termos técnicos: "CGI", "VFX", "3D", "fake", etc

3. **Extração Inteligente**:
   - Identifique o TEMA PRINCIPAL do vídeo
   - Extraia TÉCNICAS mencionadas (edição, efeitos, transições, etc)
   - Identifique FERRAMENTAS/SOFTWARE citados
   - Detecte CATEGORIA principal (tutorial, inspiração, case, técnica, etc)

4. **Hierarquia de Relevância**:
   - Título + Descrição coerentes = alta confiança
   - Só descrição boa = média confiança
   - Só hashtags/comentários = baixa confiança

5. **Detecção de FOOH (Fake Out-Of-Home / CGI Advertising)**:
   ⚠️ ATENÇÃO: FOOHs são MUITO IMPORTANTES de detectar corretamente!

   O QUE É FOOH:
   - Vídeos de publicidade usando objetos 3D/CGI em ambientes reais externos
   - "Fake" outdoor advertising (outdoor falso gerado por computador)
   - Augmented reality advertising (AR) em espaços públicos
   - Exemplos: objetos gigantes 3D "saindo" de telas outdoor, produtos flutuando em praças

   COMO DETECTAR FOOH:
   - Busque palavras-chave: "FOOH", "CGI", "3D", "fake", "augmented", "AR", "VFX", "visual effects", "outdoor", "billboard", "OOH"
   - Contextos típicos: lançamento de produtos, eventos globais (Olimpíadas, Copa do Mundo), campanhas de marca
   - Características visuais: objetos irreais/impossíveis em cenários urbanos externos
   - Hashtags comuns: #FOOH, #CGI, #3D, #OutdoorAdvertising, #FakeOOH

   SE DETECTAR FOOH:
   - SEMPRE inclua "FOOH / CGI Advertising" nas categorias
   - Adicione tags relacionadas: "fooh", "cgi", "3d", "outdoor-advertising", "vfx"
   - Na auto_description, mencione explicitamente que é um FOOH

CATEGORIAS PADRÕES (sugira 1-3 mais relevantes):
- Técnica de Edição
- Referência Visual
- Ideia de Conteúdo
- Áudio/Música
- Ferramenta/Software
- Mecânica de Campanha
- Storytelling
- Tutorial
- Case de Sucesso
- FOOH / CGI Advertising
- Outro

RETORNE APENAS JSON (sem markdown, sem explicações):
{{
  "auto_description": "string (resumo conciso 1-2 frases do QUE É o vídeo)",
  "auto_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "auto_categories": ["categoria1", "categoria2"],
  "confidence": "high|medium|low",
  "relevance_score": 0.0-1.0 (quão relevante/útil é esse vídeo como referência)
}}"""

    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return self.client is not None

# Instância global do serviço
claude_service = ClaudeService()