-- Migration to Relational Detailed SEO Data
-- This migration moves backlinks and keywords from JSONB blobs to relational tables
-- to support efficient database-level pagination.

-- 1. Domain Keywords Table
CREATE TABLE IF NOT EXISTS domain_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name VARCHAR(255) NOT NULL,
    keyword TEXT NOT NULL,
    search_volume INTEGER,
    position INTEGER,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_domain_keywords_domain ON domain_keywords(domain_name);
CREATE INDEX IF NOT EXISTS idx_domain_keywords_position ON domain_keywords(position);

-- 2. Domain Backlinks Table
CREATE TABLE IF NOT EXISTS domain_backlinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name VARCHAR(255) NOT NULL,
    source_url TEXT,
    href TEXT,
    anchor TEXT,
    domain_name_source VARCHAR(255),
    dr INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_domain_backlinks_domain ON domain_backlinks(domain_name);

-- 3. Domain Referring Domains Table
CREATE TABLE IF NOT EXISTS domain_referring_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name VARCHAR(255) NOT NULL,
    referring_domain VARCHAR(255) NOT NULL,
    backlinks_count INTEGER DEFAULT 0,
    dr INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(domain_name, referring_domain)
);

CREATE INDEX IF NOT EXISTS idx_domain_referring_domains_domain ON domain_referring_domains(domain_name);
