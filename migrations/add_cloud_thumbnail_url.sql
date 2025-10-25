-- Migration: Adicionar campo cloud_thumbnail_url para thumbnails permanentes no Supabase Storage
-- Data: 2025-10-25
-- Descrição: Armazena URL permanente da thumbnail no Supabase Storage (válida por 1 ano com signed URL)
--            Resolve problema de thumbnails quebradas quando URLs originais do YouTube/Instagram expiram

-- Adicionar coluna para URL da thumbnail na cloud
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS cloud_thumbnail_url TEXT;

-- Comentários
COMMENT ON COLUMN bookmarks.cloud_thumbnail_url IS 'URL permanente da thumbnail no Supabase Storage (signed URL válida por 1 ano). Path: {userId}/thumbnails/{bookmarkId}.jpg';

-- Index para buscas rápidas (opcional, mas útil)
CREATE INDEX IF NOT EXISTS idx_bookmarks_cloud_thumbnail_url ON bookmarks(cloud_thumbnail_url) WHERE cloud_thumbnail_url IS NOT NULL;
