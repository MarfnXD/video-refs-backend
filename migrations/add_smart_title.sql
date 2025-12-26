-- Migration: Adicionar campo smart_title para títulos otimizados para recuperação
-- Data: 2025-12-26
-- Alinhado com metodologia CODE de Tiago Forte

-- Adicionar campo smart_title
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS smart_title TEXT;

-- Comentário explicativo
COMMENT ON COLUMN bookmarks.smart_title IS 'Título gerado automaticamente pela IA, otimizado para recuperação de conhecimento (metodologia CODE). Formato: [Tema] - [Aplicação/Técnica]. Substitui títulos clickbait originais.';

-- Índice para busca rápida
CREATE INDEX IF NOT EXISTS idx_bookmarks_smart_title ON bookmarks USING gin(to_tsvector('portuguese', smart_title));

-- Observações:
-- 1. smart_title é gerado automaticamente pelo Claude durante processamento
-- 2. Baseado em: auto_description + user_context + auto_tags + visual_analysis
-- 3. Limite: 60-80 caracteres (legível em cards)
-- 4. Usuário pode editar manualmente depois (user_custom_title virá em migração futura)
-- 5. Títulos clickbait originais preservados em 'title' para referência
