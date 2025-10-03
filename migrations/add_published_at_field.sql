-- Migration: Adicionar campo published_at na tabela bookmarks
-- Data: 2025-10-01
-- Descrição: Extrair data de publicação do vídeo do metadata JSON para campo separado

-- 1. Adicionar campo published_at
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

-- 2. Criar índice para facilitar ordenação e filtros por data de publicação
CREATE INDEX IF NOT EXISTS idx_bookmarks_published_at ON bookmarks(published_at);

-- 3. Criar índice para facilitar ordenação e filtros por data de cadastro
CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at ON bookmarks(created_at);

-- 4. Comentários para documentação
COMMENT ON COLUMN bookmarks.published_at IS 'Data de publicação do vídeo na plataforma original (YouTube, Instagram, TikTok)';
COMMENT ON COLUMN bookmarks.created_at IS 'Data de cadastro do bookmark no app';
