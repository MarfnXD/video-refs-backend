-- Migration: Adicionar campos de vídeo local
-- Data: 2025-10-04

ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS local_video_path TEXT,
ADD COLUMN IF NOT EXISTS downloaded_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS video_file_size_bytes BIGINT,
ADD COLUMN IF NOT EXISTS video_quality TEXT,
ADD COLUMN IF NOT EXISTS direct_video_url TEXT;

-- Índice para buscar vídeos baixados rapidamente
CREATE INDEX IF NOT EXISTS idx_local_video_path ON bookmarks(local_video_path) WHERE local_video_path IS NOT NULL;
