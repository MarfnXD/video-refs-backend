-- Migration: Adicionar campo original_title para histórico de título
-- Data: 2025-10-03
-- Descrição: Permite editar título do card mantendo o original como referência

-- 1. Adicionar campo original_title (inicialmente NULL)
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS original_title TEXT;

-- 2. Copiar títulos atuais para original_title (apenas onde NULL)
UPDATE bookmarks
SET original_title = title
WHERE original_title IS NULL;

-- 3. Comentário para documentação
COMMENT ON COLUMN bookmarks.original_title IS 'Título original do vídeo na plataforma (imutável após primeira captura)';
COMMENT ON COLUMN bookmarks.title IS 'Título editável/customizado pelo usuário para referência pessoal';
