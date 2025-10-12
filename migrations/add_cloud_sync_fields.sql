-- =========================================
-- MIGRATION: Adicionar campos de Cloud Sync
-- =========================================
--
-- Adiciona campos para sincronização de vídeos via Supabase Storage
--
-- =========================================

-- 1. Adicionar novos campos
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS cloud_video_url TEXT,
ADD COLUMN IF NOT EXISTS cloud_upload_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS cloud_uploaded_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cloud_file_size_bytes BIGINT;

-- 2. Comentários nos campos
COMMENT ON COLUMN bookmarks.cloud_video_url IS 'URL do vídeo no Supabase Storage (signed URL válida por 1 ano)';
COMMENT ON COLUMN bookmarks.cloud_upload_status IS 'Status do upload: pending, uploading, completed, failed';
COMMENT ON COLUMN bookmarks.cloud_uploaded_at IS 'Timestamp do upload concluído';
COMMENT ON COLUMN bookmarks.cloud_file_size_bytes IS 'Tamanho do arquivo na cloud (bytes)';

-- 3. Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_cloud_upload_status
  ON bookmarks(cloud_upload_status);

CREATE INDEX IF NOT EXISTS idx_cloud_video_url
  ON bookmarks(cloud_video_url)
  WHERE cloud_video_url IS NOT NULL;

-- 4. Constraint: cloud_upload_status deve ser um dos valores válidos
ALTER TABLE bookmarks
ADD CONSTRAINT check_cloud_upload_status
  CHECK (cloud_upload_status IN ('pending', 'uploading', 'completed', 'failed'));

-- =========================================
-- ✅ MIGRATION COMPLETA!
--
-- Agora os bookmarks podem armazenar referências aos vídeos na cloud
-- =========================================
