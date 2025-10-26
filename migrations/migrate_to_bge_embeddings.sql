-- Migration para trocar de OpenAI embeddings (1536 dims) para Multilingual E5 Large (1024 dims)
-- Precisa ser executado com service role key no SQL Editor do Supabase

-- 1. Remove índice antigo
DROP INDEX IF EXISTS idx_bookmarks_embedding;

-- 2. Remove função antiga
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, float, int, uuid);

-- 3. Remove coluna antiga
ALTER TABLE bookmarks DROP COLUMN IF EXISTS embedding;

-- 4. Adiciona nova coluna embedding (1024 dimensões = multilingual-e5-large)
ALTER TABLE bookmarks
ADD COLUMN embedding vector(1024);

-- 5. Cria novo índice para busca vetorial eficiente (HNSW)
CREATE INDEX idx_bookmarks_embedding
ON bookmarks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 6. Mantém índice para acelerar queries por user_id + embedding
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_embedding
ON bookmarks (user_id)
WHERE embedding IS NOT NULL;

-- 7. Atualiza comentários
COMMENT ON COLUMN bookmarks.embedding IS 'Vetor de embedding para busca semântica (Replicate Multilingual E5 Large, 1024 dims, suporta 100 idiomas)';
COMMENT ON INDEX idx_bookmarks_embedding IS 'Índice HNSW para busca vetorial rápida por similaridade de cosseno';

-- 8. Recria função de busca semântica com nova dimensão
CREATE OR REPLACE FUNCTION search_bookmarks_semantic(
  query_embedding vector(1024),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
  filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  url text,
  title text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    b.id,
    b.url,
    b.title,
    1 - (b.embedding <=> query_embedding) AS similarity
  FROM bookmarks b
  WHERE
    b.embedding IS NOT NULL
    AND (filter_user_id IS NULL OR b.user_id = filter_user_id)
    AND 1 - (b.embedding <=> query_embedding) > match_threshold
  ORDER BY b.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION search_bookmarks_semantic IS 'Busca semântica usando Multilingual E5 Large embeddings (1024 dims) com distância de cosseno';

-- NOTA: Após executar esta migration, você precisará regenerar todos os embeddings
-- usando o script regenerate_embeddings_replicate.py
