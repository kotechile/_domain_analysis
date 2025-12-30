# N8N Scoring Workflow Setup

## Overview

The scoring workflow has been updated to use the existing Supabase function `score_and_rank_auctions`. The workflow now:

1. Loads auction data from CSV
2. Calculates semantic scores during CSV parsing
3. Calculates LFS (Lexical Frequency) scores
4. Calls the Supabase function with both scores
5. The function handles filtering, scoring, ranking, and preferred flag

## Workflow Flow

```
Webhook (CSV Upload)
  ↓
Download CSV from Storage
  ↓
Code in Python (Beta) - Parse CSV & Calculate Semantic Scores
  ├─→ Generate SQL Query → Upsert Domains → Delete Expired Records
  └─→ Prepare Scoring Data (receives semantic_scores)
       ↓
Get Scoring Config (from database)
  ↓
Prepare Scoring Data (merges config + semantic_scores)
  ↓
Calculate LFS Scores (Python)
  ↓
Prepare Function Parameters (format as JSONB)
  ↓
Call Scoring Function (Supabase function)
  ↓
Workflow Complete
```

## Key Changes

### 1. Scoring Config Table
- Created `scoring_config` table with columns:
  - `tier_1_tlds` - Array of allowed TLDs
  - `max_domain_length` - Maximum domain name length
  - `max_numbers` - Maximum digits in domain name
  - `age_weight`, `lfs_weight`, `sv_weight` - Scoring weights
  - `score_threshold`, `rank_threshold` - Preferred thresholds
  - `use_both_thresholds` - Threshold logic

### 2. Supabase Function
- Function: `score_and_rank_auctions(p_config_id, p_batch_limit, p_lfs_scores, p_semantic_scores)`
- Performs:
  - Stage 1: Filtering and scoring
  - Stage 2: Ranking calculation
  - Stage 3: Preferred flag updates
- Returns JSONB with statistics

### 3. N8N Workflow Nodes

**Prepare Scoring Data:**
- Merges config from database with semantic_scores from CSV parsing
- Passes both to next node

**Calculate LFS Scores:**
- Python node that calculates Lexical Frequency Scores
- Currently uses simplified heuristic (should query word_frequency table in production)

**Prepare Function Parameters:**
- Formats LFS and semantic scores as JSONB strings
- Prepares parameters for Supabase function call

**Call Scoring Function:**
- Executes `score_and_rank_auctions` with:
  - Config ID (or NULL for default)
  - Batch limit (10000)
  - LFS scores as JSONB
  - Semantic scores as JSONB

## Data Flow

1. **CSV Parsing** calculates `semantic_scores` dictionary:
   ```python
   semantic_scores = {
       'example.com': 75.5,
       'test.io': 60.0,
       ...
   }
   ```

2. **LFS Calculation** creates `lfs_scores` dictionary:
   ```python
   lfs_scores = {
       'example.com': 45.0,
       'test.io': 30.0,
       ...
   }
   ```

3. **Function Call** passes both as JSONB:
   ```sql
   SELECT score_and_rank_auctions(
       NULL::uuid,  -- Use default config
       10000,       -- Batch limit
       '{"example.com": 45.0, "test.io": 30.0}'::jsonb,  -- LFS scores
       '{"example.com": 75.5, "test.io": 60.0}'::jsonb   -- Semantic scores
   );
   ```

## Migration Files

1. `20251211000002_create_scoring_config_table.sql` - Creates scoring_config table
2. `20251211000003_create_basic_scoring_function.sql` - Creates score_and_rank_auctions function

## Next Steps

1. **Apply migrations** to create the table and function
2. **Re-import** the updated N8N workflow JSON
3. **Test** with a CSV upload
4. **Improve LFS calculation** to query word_frequency table instead of using heuristics

## Notes

- Semantic scores are calculated during CSV parsing using spaCy POS tagging
- LFS scores currently use a simplified heuristic (token count * 15)
- In production, LFS should query the `word_frequency` table in Supabase
- The function handles all filtering, scoring, ranking, and preferred flag logic














