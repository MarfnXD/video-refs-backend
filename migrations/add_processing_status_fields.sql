-- Migration: Adicionar campos de processamento assíncrono
-- Data: 2024-12-25
-- Descrição: Campos para rastrear status de jobs Celery

-- Adicionar campos de processamento
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'queued', 'processing', 'completed', 'failed')),
ADD COLUMN IF NOT EXISTS job_id TEXT,
ADD COLUMN IF NOT EXISTS error_message TEXT,
ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMP WITH TIME ZONE;

-- Criar índice para consultas por status
CREATE INDEX IF NOT EXISTS idx_bookmarks_processing_status ON bookmarks(processing_status);

-- Criar índice para consultas por job_id
CREATE INDEX IF NOT EXISTS idx_bookmarks_job_id ON bookmarks(job_id);

-- Criar índice composto para queries de auto-sync (bookmarks incompletos)
CREATE INDEX IF NOT EXISTS idx_bookmarks_incomplete
ON bookmarks(user_id, processing_status)
WHERE processing_status IN ('pending', 'queued', 'failed')
   OR (metadata IS NULL)
   OR (auto_tags IS NULL OR array_length(auto_tags, 1) IS NULL)
   OR (cloud_video_url IS NOT NULL AND (video_transcript IS NULL OR visual_analysis IS NULL));

-- Comentários das colunas
COMMENT ON COLUMN bookmarks.processing_status IS 'Status do processamento assíncrono: pending (não iniciado), queued (na fila), processing (em andamento), completed (concluído), failed (falhou)';
COMMENT ON COLUMN bookmarks.job_id IS 'ID do job Celery (para monitoramento e debug)';
COMMENT ON COLUMN bookmarks.error_message IS 'Mensagem de erro se processamento falhou';
COMMENT ON COLUMN bookmarks.processing_started_at IS 'Timestamp de quando processamento iniciou';
COMMENT ON COLUMN bookmarks.processing_completed_at IS 'Timestamp de quando processamento completou (sucesso ou falha)';

-- Atualizar RLS (Row Level Security) se necessário
-- Permitir que workers backend atualizem status de processamento
-- (assumindo que workers usam service_role_key que bypassa RLS)
