-- Migration: Adicionar coluna thumbnail à tabela bookmarks
-- Data: 2025-10-02

-- Adiciona coluna thumbnail (URL da imagem de preview do vídeo)
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS thumbnail TEXT;

-- Comentário explicativo
COMMENT ON COLUMN bookmarks.thumbnail IS 'URL da thumbnail/preview do vídeo (extraída via Apify)';
