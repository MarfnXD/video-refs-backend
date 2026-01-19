-- Migration: Atualizar dimensões do embedding de 1024 para 1536
-- Necessário para usar OpenAI text-embedding-3-small ao invés de Replicate

-- 1. Deletar todos os embeddings antigos (1024 dims) para evitar problemas
UPDATE bookmarks SET embedding = NULL;

-- 2. Drop a coluna antiga
ALTER TABLE bookmarks DROP COLUMN IF EXISTS embedding;

-- 3. Criar nova coluna com 1536 dimensões (OpenAI)
ALTER TABLE bookmarks ADD COLUMN embedding vector(1536);

-- 4. Atualizar a função de busca semântica para usar novo tamanho
CREATE OR REPLACE FUNCTION search_bookmarks_semantic(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    title text,
    url text,
    thumbnail text,
    similarity float
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        bookmarks.id,
        bookmarks.title,
        bookmarks.url,
        bookmarks.thumbnail,
        1 - (bookmarks.embedding <=> query_embedding) AS similarity
    FROM bookmarks
    WHERE bookmarks.embedding IS NOT NULL
        AND 1 - (bookmarks.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
