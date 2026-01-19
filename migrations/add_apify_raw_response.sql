-- Migração: Adicionar campo para armazenar resposta bruta do Apify
-- Data: 2026-01-19
-- Propósito: Debug de erros de extração de metadados

-- Adicionar coluna para resposta bruta do Apify (JSONB para queries)
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS apify_raw_response JSONB;

-- Comentário explicativo
COMMENT ON COLUMN bookmarks.apify_raw_response IS 'Resposta bruta do Apify para debug. Contém todos os campos retornados pela API.';

-- Índice para buscar por erros específicos (opcional, útil para debug)
CREATE INDEX IF NOT EXISTS idx_bookmarks_apify_error
ON bookmarks ((apify_raw_response->>'error'))
WHERE apify_raw_response->>'error' IS NOT NULL;
