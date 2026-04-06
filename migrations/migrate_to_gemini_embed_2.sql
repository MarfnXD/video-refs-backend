-- ============================================================
-- Migration: Gemini Embedding 2 (multimodal, 768 dimensoes)
-- Data: 2026-04-06
--
-- Migra de OpenAI text-embedding-3-small (1536d)
-- para Gemini Embedding 2 Preview (768d, multimodal)
--
-- IMPORTANTE: Rodar no Supabase SQL Editor
-- Projeto: twwpcnyqpwznzarguzit
-- ============================================================

-- 1. Limpar embeddings antigos (incompativeis - dimensoes diferentes)
UPDATE bookmarks SET embedding = NULL;

-- 2. Alterar dimensao do vetor para 768
ALTER TABLE bookmarks ALTER COLUMN embedding TYPE vector(768);

-- 3. Recriar index HNSW com novas dimensoes
DROP INDEX IF EXISTS idx_bookmarks_embedding;
DROP INDEX IF EXISTS idx_bookmarks_embedding_384;

CREATE INDEX idx_bookmarks_embedding ON bookmarks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 4. Recriar index composto user + embedding
DROP INDEX IF EXISTS idx_bookmarks_user_embedding;
DROP INDEX IF EXISTS idx_bookmarks_user_embedding_384;

CREATE INDEX idx_bookmarks_user_embedding ON bookmarks (user_id)
WHERE embedding IS NOT NULL;

-- 5. Atualizar search function para 768 dimensoes
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, float, int, uuid);
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, double precision, integer, uuid);
DROP FUNCTION IF EXISTS search_bookmarks_semantic(vector, double precision, integer);

CREATE OR REPLACE FUNCTION search_bookmarks_semantic(
    query_embedding vector(768),
    match_threshold double precision DEFAULT 0.7,
    match_count integer DEFAULT 10,
    filter_user_id uuid DEFAULT NULL
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
        b.id,
        b.title,
        b.url,
        b.thumbnail,
        1 - (b.embedding <=> query_embedding) AS similarity
    FROM bookmarks b
    WHERE b.embedding IS NOT NULL
        AND 1 - (b.embedding <=> query_embedding) > match_threshold
        AND (filter_user_id IS NULL OR b.user_id = filter_user_id)
    ORDER BY similarity DESC
    LIMIT match_count;
$$;

-- 6. Limpar coordenadas cached (forcar recalculo UMAP)
UPDATE bookmarks SET coord_x = NULL, coord_y = NULL, coords_last_updated = NULL;

-- Verificacao:
-- SELECT column_name, data_type, udt_name
-- FROM information_schema.columns
-- WHERE table_name = 'bookmarks' AND column_name = 'embedding';
-- Deve mostrar: udt_name = 'vector'
