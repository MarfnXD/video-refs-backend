"""
Serviço para análise de vídeo usando Gemini Flash 2.5 via Replicate API

Gemini Flash 2.5 é um modelo multimodal nativo que analisa vídeos completos:
- Áudio + Visual + Movimento
- Contexto temporal (cortes, transições, ritmo)
- Detecção de FOOH/CGI com precisão
- Transcrição automática de áudio + legendas
- Análise de técnicas de edição

Custo estimado: ~$0.015-0.025 por vídeo (30-40% mais barato que Whisper + GPT-4 Vision)
"""
import os
import replicate
from typing import Optional, Dict
import logging
import json

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        api_token = os.getenv("REPLICATE_API_TOKEN")
        if not api_token:
            logger.warning("REPLICATE_API_TOKEN não configurada - Gemini service desabilitado")
            self.client = None
        else:
            self.client = replicate.Client(api_token=api_token)

        # Modelo Gemini Flash 2.5 no Replicate (versão correta)
        # google/gemini-2.5-flash: modelo multimodal mais recente com suporte a vídeo
        self.model_version = os.getenv(
            "GEMINI_MODEL_VERSION",
            "google/gemini-2.5-flash"
        )

    async def analyze_video(
        self,
        video_url: str,
        user_context: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Analisa vídeo completo usando Gemini Flash 2.5

        Args:
            video_url: URL do vídeo (pode ser URL pública ou caminho local se via file upload)
            user_context: Contexto do usuário (opcional - peso 40% na análise!)

        Returns:
            Dict com:
            - transcript: Transcrição completa (áudio + legendas + texto na tela)
            - visual_analysis: Análise visual detalhada (técnicas, estilo, composição)
            - editing_techniques: Lista de técnicas de edição detectadas
            - storytelling: Estrutura narrativa e arco emocional
            - is_fooh: Boolean (True se for FOOH/CGI advertising)
            - technical_quality: "high" | "medium" | "low"
            - language: Idioma detectado (pt, en, es, etc)
            - confidence: 0.0-1.0 (quão confiante o modelo está)
        """
        if not self.client:
            logger.error("❌ Gemini client não inicializado (REPLICATE_API_TOKEN faltando)")
            return None

        try:
            logger.info(f"🎬 Analisando vídeo com Gemini Flash 2.5: {video_url}")

            # Montar prompt otimizado
            prompt = self._build_analysis_prompt(user_context)

            # Chamar Gemini via Replicate
            output = self.client.run(
                self.model_version,
                input={
                    "prompt": prompt,
                    "video": video_url,
                    "temperature": 0.3,  # Baixa temperatura = mais determinístico
                    "max_tokens": 4096,  # Análise detalhada
                    "top_p": 0.9,
                    "top_k": 40,
                }
            )

            # Processar output
            result = self._parse_gemini_output(output)

            if result:
                logger.info(f"✅ Vídeo analisado com sucesso - Idioma: {result.get('language')}, FOOH: {result.get('is_fooh')}")
            else:
                logger.error("❌ Falha ao parsear output do Gemini")

            return result

        except Exception as e:
            logger.error(f"❌ Erro na análise com Gemini: {str(e)}")
            return None

    def _build_analysis_prompt(self, user_context: Optional[str] = None) -> str:
        """
        Monta prompt otimizado para análise de vídeo

        Foco:
        - Transcrição completa (áudio + legendas + texto na tela)
        - Técnicas visuais e de edição
        - Detecção de FOOH/CGI
        - Estrutura narrativa
        - Qualidade técnica
        """
        base_prompt = """Você é um especialista em análise de vídeos de referência para marketing e publicidade.

Analise este vídeo COMPLETAMENTE e retorne um JSON estruturado com:

1. **transcript** (string): Transcrição COMPLETA de:
   - Todo o áudio (narração, diálogos, música com letra)
   - Todas as legendas e texto na tela
   - Descrição de sons importantes (se relevante)

2. **visual_analysis** (string): Análise visual detalhada:
   - Estilo visual (minimalista, maximalista, moderno, retrô, etc)
   - Color grading (paleta de cores, mood, contraste)
   - Composição (rule of thirds, simetria, leading lines)
   - Typography (se houver texto animado)
   - Motion graphics (animações, transições criativas)
   - Elementos CGI/3D (objetos, ambientes, efeitos)

3. **editing_techniques** (lista de strings): Técnicas de edição detectadas:
   - Tipos de corte (jump cut, match cut, L-cut, J-cut, smash cut)
   - Velocidade (slow motion, speed ramp, time remap, hyperlapse)
   - Transições (cut, dissolve, wipe, morph, glitch)
   - Ritmo de edição (fast-paced, contemplative, rhythmic, dynamic)
   - Efeitos especiais (VFX, compositing, chroma key)

4. **storytelling** (string): Estrutura narrativa:
   - Tipo (linear, não-linear, circular, montage)
   - Arco (setup → conflito → resolução, ou problema → solução)
   - Timing (quando revelações acontecem, pacing)
   - Emoção predominante (inspirador, engraçado, dramático, etc)

5. **is_fooh** (boolean): Este é um vídeo FOOH (Fake Out-Of-Home) / CGI Advertising?
   - FOOH = objetos 3D/CGI integrados em ambientes REAIS externos (outdoor)
   - Características: objeto 3D gigante, física impossível, ambiente real filmado
   - Exemplos: carro 3D saindo de billboard, produto gigante na rua, animação 3D em prédio
   - Retorne TRUE apenas se tiver CERTEZA que é FOOH

6. **technical_quality** (string): "high" | "medium" | "low"
   - high: profissional, iluminação perfeita, áudio limpo, edição polida
   - medium: semi-profissional, boa qualidade mas não impecável
   - low: amador, celular, áudio ruim, edição básica

7. **language** (string): Idioma detectado (pt, en, es, fr, etc)
   - Se múltiplos idiomas, retorne o predominante

8. **confidence** (float): 0.0-1.0
   - Quão confiante você está nesta análise?

**IMPORTANTE:**
- Seja MUITO detalhado na transcrição (capture TUDO que é dito)
- Na visual_analysis, descreva o que VÊ (não apenas categorize)
- Liste TODAS as técnicas de edição que conseguir identificar
- Se não tiver certeza se é FOOH, coloque FALSE (evite falsos positivos)

Retorne APENAS o JSON, sem texto extra:"""

        # Se usuário forneceu contexto, adicionar com peso MÁXIMO
        if user_context:
            base_prompt += f"""

**CONTEXTO DO USUÁRIO (PESO MÁXIMO - 40%):**
"{user_context}"

Use este contexto para entender POR QUE o usuário está salvando este vídeo.
Isso deve influenciar MUITO sua análise (especialmente tags e categorias que você sugeriria)."""

        return base_prompt

    def _parse_gemini_output(self, output: any) -> Optional[Dict]:
        """
        Parse output do Gemini e converte pra dict estruturado

        Gemini retorna texto (possivelmente JSON ou markdown)
        Precisa fazer parsing robusto
        """
        try:
            # Gemini pode retornar string ou iterator
            if hasattr(output, '__iter__') and not isinstance(output, str):
                output_text = ''.join(output)
            else:
                output_text = str(output)

            logger.debug(f"Output bruto do Gemini: {output_text[:500]}...")

            # Tentar parsear como JSON
            # Gemini às vezes retorna markdown com ```json ... ```
            output_text = output_text.strip()

            # Remover markdown code block se presente
            if output_text.startswith("```json"):
                output_text = output_text.replace("```json", "").replace("```", "").strip()
            elif output_text.startswith("```"):
                output_text = output_text.replace("```", "").strip()

            # Parsear JSON
            result = json.loads(output_text)

            # Validar campos obrigatórios
            required_fields = [
                'transcript', 'visual_analysis', 'editing_techniques',
                'storytelling', 'is_fooh', 'technical_quality',
                'language', 'confidence'
            ]

            for field in required_fields:
                if field not in result:
                    logger.warning(f"⚠️ Campo '{field}' faltando no output do Gemini")
                    # Adicionar default
                    if field == 'editing_techniques':
                        result[field] = []
                    elif field == 'is_fooh':
                        result[field] = False
                    elif field == 'confidence':
                        result[field] = 0.5
                    elif field == 'language':
                        result[field] = 'unknown'
                    elif field == 'technical_quality':
                        result[field] = 'medium'
                    else:
                        result[field] = ""

            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao parsear JSON do Gemini: {str(e)}")
            logger.error(f"Output problemático: {output_text[:1000]}...")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao processar output do Gemini: {str(e)}")
            return None


# Singleton instance
gemini_service = GeminiService()
