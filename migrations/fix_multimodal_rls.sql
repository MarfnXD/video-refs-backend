-- Migration: Fix RLS para permitir leitura de campos multimodais
-- Criado em: 2025-11-05
-- Motivo: Campos video_transcript, visual_analysis, transcript_language, analyzed_at
--         estão bloqueados por RLS e não aparecem no app Flutter

-- ======================================================
-- POLÍTICA DE LEITURA (SELECT) PARA CAMPOS MULTIMODAIS
-- ======================================================

-- Remove política antiga (se existir)
DROP POLICY IF EXISTS "Users can read their own bookmarks" ON bookmarks;

-- Cria nova política permitindo leitura de TODOS os campos (incluindo multimodais)
CREATE POLICY "Users can read their own bookmarks"
ON bookmarks
FOR SELECT
USING (auth.uid() = user_id);

-- Garante que RLS está habilitado
ALTER TABLE bookmarks ENABLE ROW LEVEL SECURITY;

-- ======================================================
-- VERIFICAÇÃO
-- ======================================================

-- Esta query deve funcionar APÓS aplicar a migration:
-- SELECT id, title, video_transcript, visual_analysis, transcript_language, analyzed_at
-- FROM bookmarks
-- WHERE user_id = auth.uid()
-- LIMIT 1;

COMMENT ON TABLE bookmarks IS 'Bookmarks de vídeos com metadados automáticos e análise multimodal (Whisper + GPT-4 Vision). RLS: Usuários podem ler/escrever apenas seus próprios bookmarks.';
