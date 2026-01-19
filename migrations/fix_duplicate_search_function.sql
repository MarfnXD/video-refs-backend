-- Remove função duplicada search_bookmarks_semantic
-- Fix: "Could not choose the best candidate function" error

-- 1. Remove TODAS as versões existentes da função
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, float, int);
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, double precision, integer);
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, double precision, integer, uuid);
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector(1536), float, int);
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector(1536), double precision, integer);
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector(1536), double precision, integer, uuid);

-- 2. Recria a função correta (com filter_user_id opcional)
CREATE FUNCTION search_bookmarks_semantic(
    query_embedding vector(1536),
    match_threshold double precision DEFAULT 0.7,
    match_count integer DEFAULT 10,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    title text,
    url text,
    thumbnail text,
    similarity double precision
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        bookmarks.id,
        bookmarks.title,
        bookmarks.url,
        bookmarks.thumbnail,
        (1 - (bookmarks.embedding <=> query_embedding))::double precision AS similarity
    FROM bookmarks
    WHERE bookmarks.embedding IS NOT NULL
      AND 1 - (bookmarks.embedding <=> query_embedding) > match_threshold
      AND (filter_user_id IS NULL OR bookmarks.user_id = filter_user_id)
    ORDER BY similarity DESC
    LIMIT match_count;
$$;

-- 3. Comentário explicativo
COMMENT ON FUNCTION search_bookmarks_semantic IS
'Busca semântica de bookmarks usando embeddings vetoriais (OpenAI text-embedding-3-small 1536 dims).
Opcionalmente filtra por user_id. Retorna bookmarks ordenados por similaridade.';
