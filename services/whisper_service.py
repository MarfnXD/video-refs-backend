"""
Serviço para transcrição de áudio usando Whisper via Replicate API
"""
import os
import replicate
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        api_token = os.getenv("REPLICATE_API_TOKEN")
        if not api_token:
            logger.warning("REPLICATE_API_TOKEN não configurada")
            self.client = None
        else:
            self.client = replicate.Client(api_token=api_token)

    async def transcribe_audio(self, audio_file_path: str, language: str = "pt") -> Optional[str]:
        """
        Transcreve áudio para texto usando Whisper via Replicate

        Args:
            audio_file_path: Caminho para arquivo de áudio
            language: Código do idioma (padrão: pt para português)

        Returns:
            Texto transcrito ou None se falhar
        """
        if not self.client:
            logger.error("Whisper client não inicializado (REPLICATE_API_TOKEN faltando)")
            return None

        try:
            logger.info(f"🎤 Transcrevendo áudio via Replicate: {audio_file_path}")

            # Abrir arquivo de áudio
            with open(audio_file_path, "rb") as audio_file:
                # Usar modelo Whisper no Replicate
                # https://replicate.com/openai/whisper
                output = self.client.run(
                    "openai/whisper:4d50797290df275329f202e48c76360b3f22b08d28c196cbc54600319435f8d2",
                    input={
                        "audio": audio_file,
                        "model": "large-v3",
                        "language": language,
                        "translate": False,
                        "temperature": 0,
                        "transcription": "plain text",
                        "suppress_tokens": "-1",
                        "logprob_threshold": -1.0,
                        "no_speech_threshold": 0.6,
                        "condition_on_previous_text": True,
                        "compression_ratio_threshold": 2.4,
                        "temperature_increment_on_fallback": 0.2
                    }
                )

            # Output pode ser dict com 'transcription' ou string direta
            if isinstance(output, dict):
                transcript = output.get("transcription", "") or output.get("text", "")
            else:
                transcript = str(output)

            if not transcript or not transcript.strip():
                logger.error("❌ Transcrição vazia")
                return None

            logger.info(f"✅ Transcrição concluída: {len(transcript)} caracteres")
            return transcript.strip()

        except FileNotFoundError:
            logger.error(f"❌ Arquivo de áudio não encontrado: {audio_file_path}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao transcrever áudio: {str(e)}")
            return None

    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return self.client is not None

# Instância global do serviço
whisper_service = WhisperService()