-- Migration: Add video transcript and visual analysis fields
-- Description: Adds fields for audio transcription (Whisper) and visual analysis (GPT-4 Vision)
-- Date: 2025-01-11

-- Add columns for video content analysis
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS video_transcript TEXT,
ADD COLUMN IF NOT EXISTS visual_analysis TEXT,
ADD COLUMN IF NOT EXISTS transcript_language VARCHAR(10),
ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP;

-- Add comments for documentation
COMMENT ON COLUMN bookmarks.video_transcript IS 'Audio transcription from video using Whisper API (OpenAI)';
COMMENT ON COLUMN bookmarks.visual_analysis IS 'Visual content analysis from video frames using GPT-4 Vision';
COMMENT ON COLUMN bookmarks.transcript_language IS 'Detected language of the transcript (e.g. "pt", "en", "es")';
COMMENT ON COLUMN bookmarks.analyzed_at IS 'Timestamp when video content analysis was completed';

-- Create index for searching transcripts
CREATE INDEX IF NOT EXISTS idx_bookmarks_transcript ON bookmarks USING gin(to_tsvector('english', video_transcript));
CREATE INDEX IF NOT EXISTS idx_bookmarks_visual_analysis ON bookmarks USING gin(to_tsvector('english', visual_analysis));
