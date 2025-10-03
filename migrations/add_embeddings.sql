-- Migration para adicionar suporte a embeddings e busca semântica
-- Precisa ser executado com service role key no SQL Editor do Supabase

-- 1. Habilita extensão pgvector (se ainda não estiver)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Adiciona coluna embedding (1536 dimensões = text-embedding-3-small)
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 3. Cria índice para busca vetorial eficiente (HNSW = Hierarchical Navigable Small World)
-- lists = aproximadamente sqrt(num_rows), para 1000 bookmarks ~= 32
CREATE INDEX IF NOT EXISTS idx_bookmarks_embedding
ON bookmarks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 4. Adiciona índice para acelerar queries por user_id + embedding
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_embedding
ON bookmarks (user_id)
WHERE embedding IS NOT NULL;

-- 5. Adiciona comentários
COMMENT ON COLUMN bookmarks.embedding IS 'Vetor de embedding para busca semântica (OpenAI text-embedding-3-small)';
COMMENT ON INDEX idx_bookmarks_embedding IS 'Índice HNSW para busca vetorial rápida por similaridade de cosseno';

-- 6. (Opcional) Função auxiliar para busca semântica
-- Retorna bookmarks mais similares a um vetor de query
CREATE OR REPLACE FUNCTION search_bookmarks_semantic(
  query_embedding vector(1536),
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

COMMENT ON FUNCTION search_bookmarks_semantic IS 'Busca semântica por similaridade de vetores usando distância de cosseno';
