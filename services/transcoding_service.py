"""
Serviço de transcodificação de vídeo usando FFmpeg.

Converte vídeos para H.264 Baseline Profile (compatível com todos os dispositivos Android).
"""
import subprocess
import tempfile
import os
import uuid
import httpx
from pathlib import Path


class TranscodingService:
    def __init__(self, storage_dir: str = "/opt/render/project/videos"):
        """
        Args:
            storage_dir: Diretório de armazenamento persistente para vídeos transcodificados
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def transcode_video(self, source_url: str) -> dict:
        """
        Baixa e transcodifica vídeo para H.264 Baseline Profile.

        Args:
            source_url: URL do vídeo original

        Returns:
            dict com:
                - success: bool
                - file_path: caminho do arquivo transcodificado
                - file_size_mb: tamanho do arquivo
                - error: mensagem de erro (se houver)
        """
        video_id = str(uuid.uuid4())
        temp_input = None
        output_path = self.storage_dir / f"{video_id}.mp4"

        try:
            print(f"🎬 Iniciando transcodificação para: {video_id}")

            # 1. Baixar vídeo original
            print(f"📥 Baixando vídeo de: {source_url[:50]}...")
            temp_input = await self._download_video(source_url)

            if not temp_input or not os.path.exists(temp_input):
                raise ValueError("Falha ao baixar vídeo original")

            input_size_mb = os.path.getsize(temp_input) / (1024 * 1024)
            print(f"✅ Vídeo baixado: {input_size_mb:.2f} MB")

            # 2. Transcodificar para Baseline Profile
            print(f"🔄 Transcodificando para H.264 Baseline...")
            await self._transcode_to_baseline(temp_input, str(output_path))

            if not output_path.exists():
                raise ValueError("Falha na transcodificação - arquivo não foi gerado")

            output_size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"✅ Transcodificação concluída: {output_size_mb:.2f} MB")

            return {
                "success": True,
                "file_path": str(output_path),
                "file_size_mb": round(output_size_mb, 2),
                "video_id": video_id,
            }

        except Exception as e:
            print(f"❌ Erro na transcodificação: {str(e)}")

            # Limpar arquivo de saída em caso de erro
            if output_path.exists():
                output_path.unlink()

            return {
                "success": False,
                "error": str(e),
            }

        finally:
            # Limpar arquivo temporário de entrada
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)

    async def _download_video(self, url: str, max_retries: int = 3) -> str:
        """
        Baixa vídeo para arquivo temporário com retry automático.

        Args:
            url: URL do vídeo
            max_retries: Número máximo de tentativas (padrão: 3)
        """
        import asyncio

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    print(f"⏳ Retry {attempt + 1}/{max_retries} após {wait_time}s...")
                    await asyncio.sleep(wait_time)

                async with httpx.AsyncClient(timeout=90.0) as client:  # Aumentado de 60s → 90s
                    async with client.stream('GET', url) as response:
                        response.raise_for_status()

                        with open(temp_file.name, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=8192):
                                f.write(chunk)

                print(f"✅ Vídeo baixado com sucesso (tentativa {attempt + 1})")
                return temp_file.name

            except Exception as e:
                last_error = e
                print(f"⚠️ Tentativa {attempt + 1}/{max_retries} falhou: {str(e)}")

                # Se não é a última tentativa, continua
                if attempt < max_retries - 1:
                    continue

                # Última tentativa falhou - limpar e levantar erro
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                raise ValueError(f"Erro ao baixar vídeo após {max_retries} tentativas: {str(last_error)}")

    async def _transcode_to_baseline(self, input_path: str, output_path: str):
        """
        Transcodifica vídeo para H.264 Baseline Profile usando FFmpeg.

        Parâmetros otimizados para:
        - Compatibilidade universal com Android
        - Velocidade de transcodificação (preset: fast)
        - Tamanho de arquivo reduzido
        - Qualidade aceitável para vídeos de referência
        """
        try:
            # Verifica duração do vídeo antes de transcodificar
            duration = self._get_video_duration(input_path)
            if duration and duration > 180:  # 3 minutos
                raise ValueError(f"Vídeo muito longo ({duration}s). Máximo: 180s. Use vídeos mais curtos.")

            result = subprocess.run(
                [
                    'ffmpeg',
                    '-i', input_path,

                    # Codec de vídeo: H.264 Baseline Profile
                    '-c:v', 'libx264',
                    '-profile:v', 'baseline',  # Compatibilidade universal
                    '-level', '3.0',           # Suporta até 720p

                    # Qualidade: CRF 23 (balanço qualidade/tamanho)
                    '-crf', '23',

                    # Preset: fast (30-40% mais rápido que medium)
                    # Render Starter tem 0.5 CPU, então velocidade > compressão
                    '-preset', 'fast',

                    # Limita resolução máxima (reduz carga)
                    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Garante dimensões pares

                    # Codec de áudio: AAC
                    '-c:a', 'aac',
                    '-b:a', '128k',

                    # Otimizações
                    '-movflags', '+faststart',  # Streaming otimizado
                    '-pix_fmt', 'yuv420p',      # Compatibilidade de cor

                    # Sobrescrever sem perguntar
                    '-y',

                    output_path
                ],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos timeout (Render Starter é lento)
            )

            if result.returncode != 0:
                raise ValueError(f"FFmpeg falhou: {result.stderr}")

            print(f"✅ FFmpeg concluído com sucesso")

        except subprocess.TimeoutExpired:
            raise ValueError("Transcodificação excedeu tempo limite de 10 minutos")
        except Exception as e:
            raise ValueError(f"Erro ao executar FFmpeg: {str(e)}")

    def _get_video_duration(self, video_path: str) -> float:
        """Obtém duração do vídeo em segundos usando ffprobe."""
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                print(f"⏱️ Duração do vídeo: {duration:.1f}s")
                return duration

            return None
        except Exception as e:
            print(f"⚠️ Não foi possível obter duração: {str(e)}")
            return None

    def get_video_path(self, video_id: str) -> str:
        """Retorna caminho completo do vídeo transcodificado."""
        return str(self.storage_dir / f"{video_id}.mp4")

    def video_exists(self, video_id: str) -> bool:
        """Verifica se vídeo transcodificado existe."""
        path = self.storage_dir / f"{video_id}.mp4"
        return path.exists()

    def delete_video(self, video_id: str) -> bool:
        """Deleta vídeo transcodificado."""
        try:
            path = self.storage_dir / f"{video_id}.mp4"
            if path.exists():
                path.unlink()
                print(f"🗑️ Vídeo deletado: {video_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Erro ao deletar vídeo {video_id}: {str(e)}")
            return False

    def get_storage_usage(self) -> dict:
        """Retorna estatísticas de uso de armazenamento."""
        try:
            total_size = 0
            video_count = 0

            for file_path in self.storage_dir.glob("*.mp4"):
                total_size += file_path.stat().st_size
                video_count += 1

            total_mb = total_size / (1024 * 1024)

            return {
                "video_count": video_count,
                "total_size_mb": round(total_mb, 2),
                "storage_dir": str(self.storage_dir),
            }
        except Exception as e:
            print(f"❌ Erro ao calcular armazenamento: {str(e)}")
            return {
                "video_count": 0,
                "total_size_mb": 0,
                "storage_dir": str(self.storage_dir),
                "error": str(e),
            }
