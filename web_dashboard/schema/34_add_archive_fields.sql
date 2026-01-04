-- Add archive tracking fields to research_articles table
-- These fields track archive.is submissions and archived URLs for paywalled articles

ALTER TABLE research_articles 
ADD COLUMN IF NOT EXISTS archive_submitted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS archive_checked_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS archive_url TEXT;

-- Add index for efficient querying of pending archive articles
CREATE INDEX IF NOT EXISTS idx_research_articles_archive_submitted 
ON research_articles(archive_submitted_at) 
WHERE archive_submitted_at IS NOT NULL AND archive_url IS NULL;

-- Add index for archive URL lookups
CREATE INDEX IF NOT EXISTS idx_research_articles_archive_url 
ON research_articles(archive_url) 
WHERE archive_url IS NOT NULL;

COMMENT ON COLUMN research_articles.archive_submitted_at IS 'Timestamp when URL was submitted to archive service for archiving';
COMMENT ON COLUMN research_articles.archive_checked_at IS 'Last timestamp when we checked if the article was archived';
COMMENT ON COLUMN research_articles.archive_url IS 'URL of archived version if found (archive.is/ph/md)';

