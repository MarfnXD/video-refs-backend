"""
Serviço para análise de conteúdo de vídeo (áudio + visual)
Usa Whisper API para transcrição e GPT-4 Vision para análise visual
Inclui tradução automática para português
"""
import os
import subprocess
import base64
import logging
from typing import Optional, Dict, List
from openai import OpenAI
from pathlib import Path
from services.translation_service import translate_multimodal_analysis

logger = logging.getLogger(__name__)

class VideoAnalysisService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY não configurada")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

    async def analyze_video(self, video_path: str) -> Optional[Dict]:
        """
        Analisa vídeo completo: áudio (transcrição) + visual (frames)

        Args:
            video_path: Caminho absoluto do vídeo local

        Returns:
            Dict com {
                "transcript": "texto transcrito",
                "language": "pt" ou "en",
                "visual_analysis": "descrição visual do conteúdo"
            }
        """
        if not self.client:
            logger.error("OpenAI client não inicializado")
            return None

        if not os.path.exists(video_path):
            logger.error(f"Vídeo não encontrado: {video_path}")
            return None

        try:
            logger.info(f"🎬 Iniciando análise de vídeo: {video_path}")

            # 1. Transcrever áudio
            transcript_data = await self._transcribe_audio(video_path)

            # 2. Analisar frames visualmente
            visual_analysis = await self._analyze_frames(video_path)

            # 3. Traduzir automaticamente para português (se necessário)
            transcript = transcript_data.get("text", "") if transcript_data else ""
            language = transcript_data.get("language", "") if transcript_data else ""

            translations = translate_multimodal_analysis(
                video_transcript=transcript,
                visual_analysis=visual_analysis or "",
                transcript_language=language
            )

            result = {
                "transcript": transcript,
                "language": language,
                "visual_analysis": visual_analysis or "",
                # Campos traduzidos (None se já estava em PT)
                "transcript_pt": translations.get("video_transcript_pt"),
                "visual_analysis_pt": translations.get("visual_analysis_pt")
            }

            logger.info(f"✅ Análise concluída - Transcript: {len(result['transcript'])} chars, Visual: {len(result['visual_analysis'])} chars")
            if result['transcript_pt']:
                logger.info(f"🌐 Tradução PT - Transcript: {len(result['transcript_pt'])} chars")
            if result['visual_analysis_pt']:
                logger.info(f"🌐 Tradução PT - Visual: {len(result['visual_analysis_pt'])} chars")
            return result

        except Exception as e:
            logger.error(f"❌ Erro ao analisar vídeo: {str(e)}")
            return None

    async def _transcribe_audio(self, video_path: str) -> Optional[Dict]:
        """Extrai áudio e transcreve com Whisper API"""
        try:
            logger.info("🎤 Extraindo e transcrevendo áudio...")

            # Caminho temporário para áudio
            audio_path = video_path.replace(".mp4", "_audio.mp3")

            # Extrair áudio com FFmpeg (convert to mono, 16kHz para Whisper)
            ffmpeg_cmd = [
                "ffmpeg", "-i", video_path,
                "-vn",  # Sem vídeo
                "-ar", "16000",  # Sample rate 16kHz
                "-ac", "1",  # Mono
                "-b:a", "64k",  # Bitrate
                "-y",  # Overwrite
                audio_path
            ]

            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg falhou: {result.stderr}")
                return None

            # Verificar tamanho do áudio
            audio_size = os.path.getsize(audio_path)
            if audio_size > 25 * 1024 * 1024:  # Whisper limit: 25MB
                logger.warning(f"Áudio muito grande ({audio_size/1024/1024:.1f}MB), pulando transcrição")
                os.remove(audio_path)
                return None

            # Transcrever com Whisper
            with open(audio_path, "rb") as audio_file:
                transcript_response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )

            # Limpar arquivo temporário
            os.remove(audio_path)

            transcript_data = {
                "text": transcript_response.text,
                "language": transcript_response.language
            }

            logger.info(f"✅ Transcrição concluída: {len(transcript_data['text'])} chars, idioma: {transcript_data['language']}")
            return transcript_data

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout ao extrair áudio")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao transcrever áudio: {str(e)}")
            # Limpar arquivo se existir
            if os.path.exists(audio_path):
                os.remove(audio_path)
            return None

    async def _analyze_frames(self, video_path: str) -> Optional[str]:
        """Extrai frames-chave e analisa com GPT-4 Vision"""
        try:
            logger.info("🖼️ Extraindo e analisando frames...")

            # Diretório temporário para frames
            frames_dir = os.path.join(os.path.dirname(video_path), "temp_frames")
            os.makedirs(frames_dir, exist_ok=True)

            # Extrair 4 frames igualmente espaçados (início, 1/3, 2/3, fim)
            # fps=1/X significa: capturar 1 frame a cada X segundos
            # select='eq(n,0)+eq(n,floor(N/3))+eq(n,floor(2*N/3))+eq(n,N-1)' = 4 frames

            # Primeiro, pegamos duração do vídeo
            duration_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=10)
            duration = float(duration_result.stdout.strip())

            # Extrair 4 frames em tempos específicos
            frame_times = [
                0,  # Início
                duration * 0.33,  # 1/3
                duration * 0.66,  # 2/3
                max(0, duration - 1)  # Final (1s antes do fim)
            ]

            frame_paths = []
            for i, time_sec in enumerate(frame_times):
                frame_path = os.path.join(frames_dir, f"frame_{i}.jpg")
                ffmpeg_cmd = [
                    "ffmpeg", "-ss", str(time_sec),
                    "-i", video_path,
                    "-vframes", "1",
                    "-q:v", "2",  # Alta qualidade
                    "-y",
                    frame_path
                ]
                subprocess.run(ffmpeg_cmd, capture_output=True, timeout=30)

                if os.path.exists(frame_path):
                    frame_paths.append(frame_path)

            if not frame_paths:
                logger.warning("Nenhum frame extraído")
                return None

            # Converter frames para base64
            frame_images = []
            for frame_path in frame_paths:
                with open(frame_path, "rb") as img_file:
                    img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                    frame_images.append(img_base64)

            # Análise com GPT-4 Vision
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze these 4 frames from a video and describe:

1. Main visual content (what's happening)
2. Detect if it contains:
   - CGI/3D objects in real environments (FOOH advertising)
   - Visual effects (VFX)
   - Augmented reality elements
   - Outdoor advertising/billboards
3. Filming style (animation, live-action, mixed)
4. Notable visual elements

Be concise (2-3 sentences). Focus on TECHNICAL and CREATIVE aspects.
If you detect CGI/FOOH, EXPLICITLY mention it."""
                        }
                    ]
                }
            ]

            # Adicionar as 4 imagens
            for img_base64 in frame_images:
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}",
                        "detail": "low"  # Low detail = mais barato
                    }
                })

            # Chamar GPT-4 Vision
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # gpt-4o-mini tem visão e é mais barato
                messages=messages,
                max_tokens=300,
                temperature=0.3
            )

            visual_analysis = response.choices[0].message.content

            # Limpar frames temporários
            for frame_path in frame_paths:
                os.remove(frame_path)
            os.rmdir(frames_dir)

            logger.info(f"✅ Análise visual concluída: {len(visual_analysis)} chars")
            return visual_analysis

        except Exception as e:
            logger.error(f"❌ Erro ao analisar frames: {str(e)}")
            # Limpar frames se existirem
            if os.path.exists(frames_dir):
                for f in os.listdir(frames_dir):
                    os.remove(os.path.join(frames_dir, f))
                os.rmdir(frames_dir)
            return None

    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return self.client is not None

# Instância global
video_analysis_service = VideoAnalysisService()
