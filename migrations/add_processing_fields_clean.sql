ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'queued', 'processing', 'completed', 'failed')),
ADD COLUMN IF NOT EXISTS job_id TEXT,
ADD COLUMN IF NOT EXISTS error_message TEXT,
ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_bookmarks_processing_status ON bookmarks(processing_status);

CREATE INDEX IF NOT EXISTS idx_bookmarks_job_id ON bookmarks(job_id);

CREATE INDEX IF NOT EXISTS idx_bookmarks_incomplete
ON bookmarks(user_id, processing_status)
WHERE processing_status IN ('pending', 'queued', 'failed')
   OR (metadata IS NULL)
   OR (auto_tags IS NULL OR array_length(auto_tags, 1) IS NULL)
   OR (cloud_video_url IS NOT NULL AND (video_transcript IS NULL OR visual_analysis IS NULL));
