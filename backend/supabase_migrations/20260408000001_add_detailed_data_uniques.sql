-- Add uniqueness guards for relational detailed-data tables.
-- These indexes support safer reruns and protect against accidental duplication.

CREATE UNIQUE INDEX IF NOT EXISTS idx_domain_keywords_unique
ON domain_keywords(domain_name, keyword, position, url);

CREATE UNIQUE INDEX IF NOT EXISTS idx_domain_backlinks_unique
ON domain_backlinks(domain_name, source_url, href);
