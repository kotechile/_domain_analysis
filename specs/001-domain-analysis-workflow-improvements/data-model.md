# Data Model: Domain Analysis Workflow Improvements

## Overview

This document defines the enhanced data model for the domain analysis workflow improvements, including new entities for detailed data storage and async task tracking. **Key Clarification**: This is an incremental enhancement that preserves existing data structures while adding new entities to support dual-mode operation with async pattern support.

## Core Entities

### 1. DetailedAnalysisData
**Purpose**: Store detailed analysis data (backlinks, keywords, referring domains) with metadata

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `domain_name` (VARCHAR(255), NOT NULL): Domain being analyzed
- `data_type` (VARCHAR(50), NOT NULL): Type of data (backlinks, keywords, referring_domains)
- `json_data` (JSONB, NOT NULL): Detailed data payload
- `task_id` (VARCHAR(255), NULLABLE): DataForSEO task ID for reference
- `data_source` (VARCHAR(50), DEFAULT 'dataforseo'): Source of the data
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW()): Creation timestamp
- `expires_at` (TIMESTAMP WITH TIME ZONE, NULLABLE): Expiration timestamp

**Validation Rules**:
- `domain_name` must be valid domain format
- `data_type` must be one of: 'backlinks', 'keywords', 'referring_domains'
- `json_data` must be valid JSON
- `expires_at` must be after `created_at` if provided

**Relationships**:
- One-to-many with DomainAnalysisReport (via domain_name)
- Unique constraint on (domain_name, data_type)

### 2. AsyncTask
**Purpose**: Track async DataForSEO operations and their status

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `domain_name` (VARCHAR(255), NOT NULL): Domain being analyzed
- `task_id` (VARCHAR(255), NOT NULL, UNIQUE): DataForSEO task ID
- `task_type` (VARCHAR(50), NOT NULL): Type of task (backlinks, keywords, referring_domains)
- `status` (VARCHAR(20), DEFAULT 'pending'): Task status
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW()): Creation timestamp
- `completed_at` (TIMESTAMP WITH TIME ZONE, NULLABLE): Completion timestamp
- `error_message` (TEXT, NULLABLE): Error message if failed
- `retry_count` (INTEGER, DEFAULT 0): Number of retry attempts

**Validation Rules**:
- `task_id` must be unique across all tasks
- `task_type` must be one of: 'backlinks', 'keywords', 'referring_domains'
- `status` must be one of: 'pending', 'processing', 'completed', 'failed'
- `retry_count` must be >= 0
- `completed_at` must be after `created_at` if provided

**Relationships**:
- One-to-many with DomainAnalysisReport (via domain_name)

### 3. DomainAnalysisReport (Enhanced)
**Purpose**: Main report entity with enhanced fields for detailed data tracking

**New Fields**:
- `detailed_data_available` (JSONB, DEFAULT '{}'): Tracks which detailed data types are available
- `analysis_phase` (VARCHAR(50), DEFAULT 'essential'): Current analysis phase
- `analysis_mode` (VARCHAR(20), DEFAULT 'legacy'): Analysis mode (legacy, async, dual)
- `progress_data` (JSONB, NULLABLE): Progress tracking for async operations

**Enhanced Fields**:
- `data_for_seo_metrics` (JSONB): Enhanced with detailed data references
- `llm_analysis` (JSONB): Enhanced with comprehensive analysis including quality scores

**Validation Rules**:
- `analysis_phase` must be one of: 'essential', 'detailed', 'ai_analysis', 'completed'
- `analysis_mode` must be one of: 'legacy', 'async', 'dual'
- `detailed_data_available` must be valid JSON object with boolean values
- `progress_data` must be valid JSON object if provided

### 4. AnalysisModeConfig
**Purpose**: Configuration for dual-mode operation and feature flags

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `domain_name` (VARCHAR(255), NULLABLE): Domain-specific config (NULL for global)
- `mode_preference` (VARCHAR(20), DEFAULT 'dual'): Preferred analysis mode
- `async_enabled` (BOOLEAN, DEFAULT true): Enable async pattern
- `cache_ttl_hours` (INTEGER, DEFAULT 24): Cache TTL in hours
- `manual_refresh_enabled` (BOOLEAN, DEFAULT true): Enable manual refresh
- `progress_indicators_enabled` (BOOLEAN, DEFAULT true): Enable progress tracking
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW()): Creation timestamp
- `updated_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW()): Last update timestamp

**Validation Rules**:
- `mode_preference` must be one of: 'legacy', 'async', 'dual'
- `cache_ttl_hours` must be between 1 and 168 (1 hour to 1 week)
- `domain_name` must be valid domain format if provided

## Data Types and Enums

### DetailedDataType
```python
class DetailedDataType(str, Enum):
    BACKLINKS = "backlinks"
    KEYWORDS = "keywords"
    REFERRING_DOMAINS = "referring_domains"
```

### AsyncTaskStatus
```python
class AsyncTaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

### AnalysisPhase
```python
class AnalysisPhase(str, Enum):
    ESSENTIAL = "essential"
    DETAILED = "detailed"
    AI_ANALYSIS = "ai_analysis"
    COMPLETED = "completed"
```

### AnalysisMode
```python
class AnalysisMode(str, Enum):
    LEGACY = "legacy"
    ASYNC = "async"
    DUAL = "dual"
```

### ProgressStatus
```python
class ProgressStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

## JSONB Schema Definitions

### Detailed Backlinks Data
```json
{
  "total_count": 1234,
  "items": [
    {
      "url_from": "https://example.com/page",
      "url_to": "https://target.com/page",
      "domain_from": "example.com",
      "domain_from_rank": 75,
      "anchor": "link text",
      "first_seen": "2023-01-01",
      "last_seen": "2023-12-31",
      "backlink_status": "active",
      "dofollow": true,
      "link_type": "text",
      "link_attributes": ["nofollow", "ugc"]
    }
  ]
}
```

### Detailed Keywords Data
```json
{
  "total_count": 567,
  "items": [
    {
      "keyword": "example keyword",
      "keyword_difficulty": 45,
      "search_volume": 1000,
      "cpc": 1.50,
      "competition": 0.7,
      "search_intent": "informational",
      "keyword_properties": {
        "is_question": false,
        "is_local": false,
        "is_news": false
      }
    }
  ]
}
```

### Detailed Referring Domains Data
```json
{
  "total_count": 89,
  "items": [
    {
      "domain": "example.com",
      "domain_rank": 75,
      "backlinks_count": 5,
      "first_seen": "2023-01-01",
      "last_seen": "2023-12-31",
      "domain_type": "com",
      "country": "US",
      "language": "en"
    }
  ]
}
```

### Enhanced LLM Analysis
```json
{
  "summary": "Comprehensive analysis summary",
  "strengths": ["High domain authority", "Diverse backlink profile"],
  "weaknesses": ["Limited keyword diversity", "Low search volume"],
  "backlink_quality_score": 8.5,
  "keyword_opportunity_score": 6.2,
  "investment_recommendation": "Strong buy",
  "key_metrics": {
    "domain_authority": "High (DR 75+)",
    "backlink_profile_health": "Excellent",
    "keyword_potential": "Moderate",
    "technical_seo": "Good"
  },
  "recommendations": [
    "Focus on long-tail keywords",
    "Build more high-authority backlinks"
  ]
}
```

## State Transitions

### Analysis Phase Transitions
```
essential → detailed → ai_analysis → completed
    ↓           ↓           ↓
  failed     failed     failed
```

**Transition Rules**:
- `essential` → `detailed`: After essential data collection completes
- `detailed` → `ai_analysis`: After detailed data collection completes
- `ai_analysis` → `completed`: After AI analysis completes successfully
- Any phase → `failed`: On critical error

### Async Task Status Transitions
```
pending → processing → completed
    ↓         ↓
  failed    failed
```

**Transition Rules**:
- `pending` → `processing`: When task is submitted to DataForSEO
- `processing` → `completed`: When task completes successfully
- `pending`/`processing` → `failed`: On error or timeout

## Database Constraints

### Primary Keys
- `DetailedAnalysisData.id`
- `AsyncTask.id`
- `DomainAnalysisReport.id` (existing)

### Unique Constraints
- `DetailedAnalysisData(domain_name, data_type)`
- `AsyncTask.task_id`

### Foreign Keys
- `DetailedAnalysisData.domain_name` → `DomainAnalysisReport.domain_name`
- `AsyncTask.domain_name` → `DomainAnalysisReport.domain_name`

### Check Constraints
- `DetailedAnalysisData.data_type` IN ('backlinks', 'keywords', 'referring_domains')
- `AsyncTask.task_type` IN ('backlinks', 'keywords', 'referring_domains')
- `AsyncTask.status` IN ('pending', 'processing', 'completed', 'failed')
- `DomainAnalysisReport.analysis_phase` IN ('essential', 'detailed', 'ai_analysis', 'completed')
- `AsyncTask.retry_count` >= 0

## Indexes

### Performance Indexes
```sql
-- Detailed data queries
CREATE INDEX idx_detailed_data_domain_type ON detailed_analysis_data(domain_name, data_type);
CREATE INDEX idx_detailed_data_expires_at ON detailed_analysis_data(expires_at);

-- Async task queries
CREATE INDEX idx_async_tasks_domain_type ON async_tasks(domain_name, task_type);
CREATE INDEX idx_async_tasks_status ON async_tasks(status);
CREATE INDEX idx_async_tasks_task_id ON async_tasks(task_id);

-- Report queries
CREATE INDEX idx_reports_analysis_phase ON reports(analysis_phase);
```

### JSONB Indexes
```sql
-- For detailed data queries
CREATE INDEX idx_detailed_data_jsonb_gin ON detailed_analysis_data USING GIN (json_data);

-- For LLM analysis queries
CREATE INDEX idx_reports_llm_analysis_gin ON reports USING GIN (llm_analysis);
```

## Data Migration Strategy

### Phase 1: Schema Creation
1. Create new tables with constraints
2. Add new columns to existing tables
3. Create indexes for performance

### Phase 2: Data Population
1. Migrate existing reports to new schema
2. Populate detailed_data_available based on existing data
3. Set analysis_phase based on current status

### Phase 3: Validation
1. Verify data integrity
2. Test query performance
3. Validate constraints

## Data Retention and Cleanup

### Retention Policies
- Detailed data: 30 days (configurable)
- Async tasks: 7 days after completion
- Failed tasks: 1 day after last retry

### Cleanup Procedures
```sql
-- Clean up expired detailed data
DELETE FROM detailed_analysis_data 
WHERE expires_at < NOW();

-- Clean up old async tasks
DELETE FROM async_tasks 
WHERE completed_at < NOW() - INTERVAL '7 days'
AND status = 'completed';

-- Clean up failed tasks
DELETE FROM async_tasks 
WHERE created_at < NOW() - INTERVAL '1 day'
AND status = 'failed';
```

## Security Considerations

### Row Level Security (RLS)
```sql
-- Detailed data access
CREATE POLICY "Public can read detailed data" ON detailed_analysis_data 
FOR SELECT USING (true);

-- Service role can manage detailed data
CREATE POLICY "Service role can manage detailed data" ON detailed_analysis_data 
FOR ALL USING (auth.role() = 'service_role');

-- Async task access
CREATE POLICY "Service role can manage async tasks" ON async_tasks 
FOR ALL USING (auth.role() = 'service_role');
```

### Data Encryption
- All data encrypted in transit (TLS)
- Sensitive data encrypted at rest
- API keys stored securely in environment variables

## Performance Considerations

### Query Optimization
- Use appropriate indexes for common queries
- Implement pagination for large datasets
- Optimize JSONB queries with proper operators

### Caching Strategy
- Cache detailed data for 24 hours
- Use database-level caching
- Implement cache invalidation

### Monitoring
- Track query performance
- Monitor cache hit rates
- Alert on slow queries
