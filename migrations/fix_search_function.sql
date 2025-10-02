-- Fix para a função search_bookmarks_semantic
-- Corrige erro de type mismatch entre varchar e text

DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, float, int, uuid);

CREATE OR REPLACE FUNCTION search_bookmarks_semantic(
  query_embedding vector(384),
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
    b.url::text,
    b.title::text,  -- CAST para text
    (1 - (b.embedding <=> query_embedding))::float AS similarity
  FROM bookmarks b
  WHERE
    b.embedding IS NOT NULL
    AND (filter_user_id IS NULL OR b.user_id = filter_user_id)
    AND 1 - (b.embedding <=> query_embedding) > match_threshold
  ORDER BY b.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION search_bookmarks_semantic IS 'Busca semântica por similaridade de vetores usando distância de cosseno (384 dim) - CORRIGIDO';
