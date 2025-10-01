-- Migration: Add automatic metadata processing fields
-- Description: Adds fields for AI-processed metadata without user context
-- Date: 2024-09-30

-- Add columns for automatic metadata processing
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS auto_description TEXT,
ADD COLUMN IF NOT EXISTS auto_tags TEXT[],
ADD COLUMN IF NOT EXISTS auto_categories TEXT[],
ADD COLUMN IF NOT EXISTS relevance_score FLOAT DEFAULT 0.5;

-- Add comments for documentation
COMMENT ON COLUMN bookmarks.auto_description IS 'AI-generated description based on video metadata (title, description, hashtags, comments)';
COMMENT ON COLUMN bookmarks.auto_tags IS 'AI-generated tags extracted from video metadata (separate from manual tags)';
COMMENT ON COLUMN bookmarks.auto_categories IS 'AI-generated categories from video metadata (separate from manual categories)';
COMMENT ON COLUMN bookmarks.relevance_score IS 'AI confidence score for how relevant/useful this video is as a reference (0.0-1.0)';

-- Create index for searching auto_tags
CREATE INDEX IF NOT EXISTS idx_bookmarks_auto_tags ON bookmarks USING GIN (auto_tags);
CREATE INDEX IF NOT EXISTS idx_bookmarks_auto_categories ON bookmarks USING GIN (auto_categories);

-- Add constraint for relevance_score range
ALTER TABLE bookmarks
ADD CONSTRAINT check_relevance_score_range CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0);
