-- Migration: Adicionar campo para comentários filtrados (50 melhores)
-- Criado em: 2025-11-05
-- Motivo: Salvar os 50 melhores comentários usados pela IA para gerar tags/categorias
--         Útil para auditoria, debugging e visualização no app

-- Adiciona campo filtered_comments (JSONB array)
-- Estrutura: [{text: string, likes: number, author: string}]
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS filtered_comments JSONB DEFAULT NULL;

-- Comentário explicativo
COMMENT ON COLUMN bookmarks.filtered_comments IS
'Array JSON com os 50 melhores comentários filtrados (removidos genéricos) usados pela IA.
Estrutura: [{text: string, likes: number, author: string}]
Útil para auditoria e visualização no app.';

-- Criar índice para facilitar queries
CREATE INDEX IF NOT EXISTS idx_bookmarks_filtered_comments
ON bookmarks USING GIN (filtered_comments);

-- Índice para buscar bookmarks que TÊM comentários filtrados
CREATE INDEX IF NOT EXISTS idx_bookmarks_has_filtered_comments
ON bookmarks ((filtered_comments IS NOT NULL))
WHERE filtered_comments IS NOT NULL;
