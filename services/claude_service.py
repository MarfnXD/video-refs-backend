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
        return f"""Você é um assistente especializado em analisar vídeos de referência criativa.

ANALISE OS METADADOS ABAIXO E EXTRAIA INFORMAÇÕES RELEVANTES:

👤 CONTEXTO MANUAL DO USUÁRIO (peso 40% - ⭐ PRIORIDADE MÁXIMA):
{user_context if user_context else 'Não fornecido'}
(Se fornecido, este é o motivo pelo qual o usuário salvou o vídeo - DEVE ter PESO MÁXIMO na análise!
O auto_description DEVE refletir este contexto se disponível.)

🖼️ ANÁLISE VISUAL (peso 35% - 🎯 FONTE MAIS CONFIÁVEL):
{visual_analysis if visual_analysis else 'Não disponível'}
(Análise automática de frames do vídeo via GPT-4 Vision - detecta CGI, VFX, FOOH, elementos visuais reais)
⚠️ CRÍTICO: Se a análise visual contradiz outros dados (comentários, título), SEMPRE priorize a análise visual!
Ela descreve o que REALMENTE está sendo mostrado no vídeo, não interpretações pessoais.

🎤 TRANSCRIÇÃO DE ÁUDIO (peso 25%):
{video_transcript if video_transcript else 'Não disponível'}
(Transcrição automática do áudio do vídeo via Whisper AI - revela narrações, diálogos, técnicas mencionadas)

📌 TÍTULO (peso 12%): "{title}"

📄 DESCRIÇÃO (peso 10%):
"{description or 'Não disponível'}"

#️⃣ HASHTAGS (peso 8%):
{hashtags_str}

💬 COMENTÁRIOS TOP FILTRADOS (peso 5% - ⚠️ MENOR PRIORIDADE):
{comments_str}
(Comentários genéricos já foram filtrados. ATENÇÃO: Comentários são interpretações PESSOAIS de usuários,
podem estar completamente errados sobre o conteúdo real do vídeo. Use apenas como contexto secundário.
Se comentários contradizem análise visual/transcrição, IGNORE os comentários!)

INSTRUÇÕES DE ANÁLISE:
1. **⭐ PRIORIZE O CONTEXTO DO USUÁRIO ACIMA DE TUDO** (SE FORNECIDO):
   - O contexto do usuário é o motivo REAL pelo qual ele salvou este vídeo
   - Se fornecido, o auto_description DEVE começar refletindo este contexto
   - Exemplo: Contexto="ref de transições suaves" → auto_description="Vídeo demonstrando técnicas de transições suaves..."
   - Tags e categorias devem ser extraídas considerando PRINCIPALMENTE o contexto do usuário

2. **Validação de Consistência**:
   - Se o título NÃO se relaciona com a descrição, reduza o peso do título
   - Se título for genérico tipo "😱", "TRENDING", priorize descrição/hashtags

3. **⚠️ ANÁLISE VISUAL TEM PRIORIDADE ABSOLUTA SOBRE COMENTÁRIOS** (CRÍTICO):
   - A análise visual descreve o que REALMENTE está no vídeo (CGI, objetos, cenários, técnicas)
   - Comentários são interpretações PESSOAIS de usuários (podem estar completamente errados!)
   - REGRA DE OURO: Se análise visual diz "cena celestial com CGI" mas comentários dizem "religião",
     você DEVE basear tags/categorias na análise visual, NÃO nos comentários
   - Comentários SÓ devem ser usados se NÃO contradizem análise visual/transcrição

4. **Priorize ANÁLISE VISUAL e TRANSCRIÇÃO** (MUITO IMPORTANTE):
   - Análise Visual (35%): detecta o que é MOSTRADO (CGI, FOOH, VFX, objetos 3D, cenários reais)
   - Transcrição (25%): revela o que é DITO (narrações sobre técnicas, produtos, conceitos)
   - Estes são dados OBJETIVOS, não interpretações
   - Se análise visual mencionar "CGI", "FOOH", "3D objects", "cosmic scene" → PRIORIZE isso acima de tudo!

5. **Extração Inteligente**:
   - Identifique o TEMA PRINCIPAL do vídeo
   - Extraia TÉCNICAS mencionadas (edição, efeitos, transições, etc)
   - Identifique FERRAMENTAS/SOFTWARE citados
   - Detecte CATEGORIA principal (tutorial, inspiração, case, técnica, etc)

6. **Hierarquia de Relevância (ORDEM DE PRIORIDADE)**:
   1️⃣ Contexto do usuário fornecido = ALTÍSSIMA confiança (40% - peso máximo!)
   2️⃣ Análise Visual = ALTA confiança (35% - descreve o que está REALMENTE no vídeo)
   3️⃣ Transcrição = alta confiança (25% - revela o que é dito/cantado)
   4️⃣ Título + Descrição coerentes = média confiança (12% + 10%)
   5️⃣ Hashtags = baixa confiança (8%)
   6️⃣ Comentários = BAIXÍSSIMA confiança (5% - interpretações pessoais, podem estar errados)

   ⚠️ SE HOUVER CONTRADIÇÃO: Análise Visual > Transcrição > Título/Descrição > Hashtags > Comentários

7. **Detecção de FOOH (Fake Out-Of-Home / CGI Advertising)**:
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