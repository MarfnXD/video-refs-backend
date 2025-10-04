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

    async def _download_video(self, url: str) -> str:
        """Baixa vídeo para arquivo temporário."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream('GET', url) as response:
                    response.raise_for_status()

                    with open(temp_file.name, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)

            return temp_file.name

        except Exception as e:
            # Limpar em caso de erro
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise ValueError(f"Erro ao baixar vídeo: {str(e)}")

    async def _transcode_to_baseline(self, input_path: str, output_path: str):
        """
        Transcodifica vídeo para H.264 Baseline Profile usando FFmpeg.

        Parâmetros otimizados para:
        - Compatibilidade universal com Android
        - Tamanho de arquivo reduzido
        - Qualidade aceitável para vídeos de referência
        """
        try:
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

                    # Preset: medium (balanço velocidade/compressão)
                    '-preset', 'medium',

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
                timeout=300  # 5 minutos timeout
            )

            if result.returncode != 0:
                raise ValueError(f"FFmpeg falhou: {result.stderr}")

            print(f"✅ FFmpeg concluído com sucesso")

        except subprocess.TimeoutExpired:
            raise ValueError("Transcodificação excedeu tempo limite de 5 minutos")
        except Exception as e:
            raise ValueError(f"Erro ao executar FFmpeg: {str(e)}")

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
