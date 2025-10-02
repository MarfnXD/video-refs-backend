"""
Serviço para upload de thumbnails no Supabase Storage.

Faz download de thumbnails temporárias e salva permanentemente no Supabase Storage.
"""

import os
import httpx
import hashlib
from typing import Optional
from supabase import create_client, Client


class StorageService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        # Usar SERVICE_ROLE key para ter permissões de upload/admin
        self.supabase_key = os.getenv("SUPABASE_KEY")  # NUNCA hardcode esta chave!
        self.bucket_name = "thumbnails"

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar definidas nas variáveis de ambiente!")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Criar bucket se não existir
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Garante que o bucket de thumbnails existe."""
        try:
            # Tentar listar buckets
            buckets = self.supabase.storage.list_buckets()
            bucket_exists = any(b['name'] == self.bucket_name for b in buckets)

            if not bucket_exists:
                # Criar bucket público
                self.supabase.storage.create_bucket(
                    self.bucket_name,
                    options={"public": True}
                )
                print(f"✅ Bucket '{self.bucket_name}' criado")
        except Exception as e:
            print(f"⚠️ Erro ao verificar/criar bucket: {e}")
            # Bucket pode já existir

    def _generate_filename(self, original_url: str, video_url: str) -> str:
        """
        Gera nome de arquivo único baseado na URL do vídeo.

        Args:
            original_url: URL original da thumbnail
            video_url: URL do vídeo (para gerar hash único)

        Returns:
            Nome do arquivo (ex: "abc123.jpg")
        """
        # Usar hash da URL do vídeo como identificador único
        hash_obj = hashlib.md5(video_url.encode())
        hash_str = hash_obj.hexdigest()[:12]

        # Determinar extensão da imagem
        ext = ".jpg"  # padrão
        if ".png" in original_url.lower():
            ext = ".png"
        elif ".webp" in original_url.lower():
            ext = ".webp"

        return f"{hash_str}{ext}"

    async def upload_thumbnail(
        self,
        thumbnail_url: str,
        video_url: str
    ) -> Optional[str]:
        """
        Faz download de uma thumbnail e faz upload no Supabase Storage.

        Args:
            thumbnail_url: URL temporária da thumbnail
            video_url: URL do vídeo (para gerar nome único)

        Returns:
            URL permanente da thumbnail no Supabase Storage ou None se falhar
        """
        try:
            # Gerar nome de arquivo único
            filename = self._generate_filename(thumbnail_url, video_url)

            # Verificar se já existe
            try:
                existing = self.supabase.storage.from_(self.bucket_name).list(path="")
                if any(f['name'] == filename for f in existing):
                    # Já existe, retornar URL
                    public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(filename)
                    return public_url
            except:
                pass  # Continuar com upload

            # Fazer download da thumbnail
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(thumbnail_url)

                if response.status_code != 200:
                    print(f"❌ Falha ao baixar thumbnail: HTTP {response.status_code}")
                    return None

                image_data = response.content

            # Upload para Supabase Storage
            self.supabase.storage.from_(self.bucket_name).upload(
                path=filename,
                file=image_data,
                file_options={"content-type": response.headers.get("content-type", "image/jpeg")}
            )

            # Obter URL pública
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(filename)

            print(f"✅ Thumbnail salva: {filename}")
            return public_url

        except httpx.TimeoutException:
            print(f"⏱️ Timeout ao baixar thumbnail")
            return None
        except Exception as e:
            print(f"❌ Erro ao fazer upload de thumbnail: {str(e)}")
            return None


# Singleton
storage_service = StorageService()
