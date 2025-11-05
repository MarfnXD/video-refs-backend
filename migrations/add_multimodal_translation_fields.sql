-- Migration: Adicionar campos de tradução para análise multimodal
-- Criado em: 2025-11-05
-- Motivo: Permitir tradução automática de transcrições e análises visuais
--         mantendo versão original + tradução PT para busca multilíngue

-- ======================================================
-- CAMPOS DE TRADUÇÃO
-- ======================================================

-- Adiciona campo de transcrição traduzida (PT)
ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS video_transcript_pt TEXT;

-- Adiciona campo de análise visual traduzida (PT)
ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS visual_analysis_pt TEXT;

-- ======================================================
-- COMENTÁRIOS
-- ======================================================

COMMENT ON COLUMN bookmarks.video_transcript IS 'Transcrição original do áudio (Whisper API) - idioma detectado em transcript_language';
COMMENT ON COLUMN bookmarks.video_transcript_pt IS 'Transcrição traduzida para português (GPT-4o-mini) - NULL se já estava em PT';
COMMENT ON COLUMN bookmarks.visual_analysis IS 'Análise visual original dos frames (GPT-4 Vision) - geralmente em inglês';
COMMENT ON COLUMN bookmarks.visual_analysis_pt IS 'Análise visual traduzida para português (GPT-4o-mini) - NULL se já estava em PT';

-- ======================================================
-- ÍNDICES (Busca Full-Text)
-- ======================================================

-- Índice GIN para busca full-text na transcrição PT
CREATE INDEX IF NOT EXISTS idx_bookmarks_video_transcript_pt_gin
ON bookmarks USING gin(to_tsvector('portuguese', video_transcript_pt));

-- Índice GIN para busca full-text na análise visual PT
CREATE INDEX IF NOT EXISTS idx_bookmarks_visual_analysis_pt_gin
ON bookmarks USING gin(to_tsvector('portuguese', visual_analysis_pt));

-- ======================================================
-- VERIFICAÇÃO
-- ======================================================

-- Após aplicar migration, verificar:
-- SELECT
--   id,
--   title,
--   transcript_language,
--   video_transcript IS NOT NULL as has_original_transcript,
--   video_transcript_pt IS NOT NULL as has_pt_transcript,
--   visual_analysis IS NOT NULL as has_original_visual,
--   visual_analysis_pt IS NOT NULL as has_pt_visual
-- FROM bookmarks
-- WHERE video_transcript IS NOT NULL OR visual_analysis IS NOT NULL
-- LIMIT 10;

COMMENT ON TABLE bookmarks IS 'Bookmarks de vídeos com metadados automáticos, análise multimodal (Whisper + GPT-4 Vision) e tradução automática PT. RLS: Usuários podem ler/escrever apenas seus próprios bookmarks.';
