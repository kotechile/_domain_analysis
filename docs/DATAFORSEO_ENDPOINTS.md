# DataForSEO API Endpoints Used in This Project

This document lists all DataForSEO API endpoints used in the domain analysis system and their purposes.

## Overview

The system uses DataForSEO APIs in two ways:
1. **Direct API calls** - Made directly from the backend
2. **Via N8N workflows** - Backend triggers N8N, which calls DataForSEO and returns results via webhook

---

## 1. Backlinks Summary

### Endpoint
- **Direct**: `/backlinks/summary/live`
- **Via N8N**: Triggered through N8N workflow (webhook: `/webhook/webhook/backlinks`)

### Purpose
Get aggregated backlink statistics for a domain:
- Total backlinks count
- Total referring domains count
- Domain rank (PageRank-like metric, 0-1000 scale)
- First seen date
- Last seen date

### Usage
- **When**: During essential data collection phase (initial domain analysis)
- **Method**: `DataForSEOService.get_backlinks_summary()` or `N8NService.trigger_backlinks_summary_workflow()`
- **Location**: `backend/src/services/external_apis.py` (line 368) and `backend/src/services/n8n_service.py` (line 124)
- **Cached**: Yes (24 hours)

### Request Format
```json
{
  "0": {
    "target": "example.com",
    "internal_list_limit": 10,
    "include_subdomains": true,
    "backlinks_filters": ["dofollow", "=", true],
    "backlinks_status_type": "all"
  }
}
```

### Response Data Used
- `backlinks` - Total number of backlinks
- `referring_domains` - Total number of unique referring domains
- `rank` - DataForSEO domain rank (0-1000 scale, converted to 0-100 for DR)

---

## 2. Detailed Backlinks

### Endpoint
- **Direct Live**: `/backlinks/backlinks/live`
- **Direct Async**: `/backlinks/backlinks/task_post` → `/backlinks/backlinks/task_get`
- **Via N8N**: Triggered through N8N workflow (webhook: `/webhook/webhook/backlinks-details`)

### Purpose
Get individual backlink records with detailed information:
- Source domain and URL
- Target URL
- Anchor text
- Domain rank of referring domain
- Link attributes (dofollow/nofollow)
- First seen / Last seen dates
- Link type and status

### Usage
- **When**: On-demand when user requests detailed backlinks (not during initial analysis to save costs)
- **Method**: 
  - `DataForSEOService.get_detailed_backlinks()` (live, limit: 100-1000)
  - `DataForSEOAsyncService.get_detailed_backlinks_async()` (async, limit: up to 10,000)
  - `N8NService.trigger_backlinks_workflow()` (via N8N)
- **Location**: 
  - `backend/src/services/external_apis.py` (line 423)
  - `backend/src/services/dataforseo_async.py` (line 41)
  - `backend/src/services/n8n_service.py` (line 30)

### Request Format
```json
{
  "0": {
    "target": "example.com",
    "limit": 10000,
    "mode": "as_is",
    "filters": ["dofollow", "=", true]
  }
}
```

### Response Data Used
- `items[]` - Array of individual backlink records
- Each item contains: `domain_from`, `url_from`, `url_to`, `anchor`, `domain_from_rank`, `dofollow`, `first_seen`, `last_seen`, etc.

---

## 3. Domain Rank Overview

### Endpoint
- **Direct**: `/dataforseo_labs/google/domain_rank_overview/live`

### Purpose
Get comprehensive domain ranking and traffic metrics:
- Organic search metrics (traffic estimates, keyword counts, impressions)
- Paid search metrics
- Domain ranking distribution
- Estimated traffic value (ETV)

### Usage
- **When**: During essential data collection phase (initial domain analysis)
- **Method**: `DataForSEOService.get_domain_analytics()`
- **Location**: `backend/src/services/external_apis.py` (line 64)
- **Cached**: Yes (24 hours)
- **Note**: This is NOT backlinks-related, so it's called directly (not via N8N)

### Request Format
```json
{
  "0": {
    "target": "example.com",
    "language_name": "English",
    "location_code": 2840
  }
}
```

### Response Data Used
- `metrics.organic.etv` - Estimated Traffic Value (organic)
- `metrics.organic.count` - Total keywords ranking
- `metrics.organic.impressions` - Total impressions
- `metrics.paid.*` - Paid search metrics

---

## 4. Ranked Keywords

### Endpoint
- **Direct Live**: `/dataforseo_labs/google/ranked_keywords/live`
- **Direct Async**: `/dataforseo_labs/google/ranked_keywords/task_post` → `/dataforseo_labs/google/ranked_keywords/task_get`
- **Tasks Ready**: `/dataforseo_labs/google/ranked_keywords/tasks_ready`

### Purpose
Get list of keywords that a domain ranks for in Google search:
- Keyword text
- Search volume
- Current ranking position
- CPC (Cost Per Click)
- Competition level
- Estimated traffic value (ETV)
- SERP details (URL, title, description)

### Usage
- **When**: On-demand when user requests detailed keywords (not during initial analysis to save costs)
- **Method**: 
  - `DataForSEOService.get_detailed_keywords()` (live, limit: 1000)
  - `DataForSEOAsyncService.get_detailed_keywords_async()` (async, limit: up to 10,000)
- **Location**: 
  - `backend/src/services/external_apis.py` (line 470)
  - `backend/src/services/dataforseo_async.py` (line 56)
- **Note**: This is NOT backlinks-related, so it's called directly (not via N8N)

### Request Format
```json
{
  "0": {
    "target": "example.com",
    "language_name": "English",
    "location_name": "United States",
    "load_rank_absolute": true,
    "limit": 10000
  }
}
```

### Response Data Used
- `items[]` - Array of keyword ranking records
- Each item contains: `keyword_data.keyword`, `ranked_serp_element.serp_item.rank_absolute`, `keyword_data.keyword_info.search_volume`, `keyword_data.keyword_info.cpc`, etc.

### Data Filtering
- Filters out sample/test keywords pointing to `dataforseo.com`, `example.com`, `test.com`, etc.
- Validates that keywords are actually related to the target domain

---

## 5. Referring Domains

### Endpoint
- **Direct Live**: `/backlinks/backlinks/live` (with aggregation)
- **Direct Async**: `/backlinks/backlinks/task_post` → `/backlinks/backlinks/task_get`
- **Tasks Ready**: `/backlinks/backlinks/tasks_ready`

### Purpose
Get list of unique referring domains (domains that link to the target):
- Domain name
- Domain rank
- Number of backlinks from that domain
- First seen / Last seen dates

### Usage
- **When**: On-demand when user requests referring domains (not during initial analysis to save costs)
- **Method**: 
  - `DataForSEOService.get_referring_domains()` (live, limit: 800)
  - `DataForSEOAsyncService.get_referring_domains_async()` (async, limit: up to 10,000)
- **Location**: 
  - `backend/src/services/external_apis.py` (line 518)
  - `backend/src/services/dataforseo_async.py` (line 72)
- **Note**: Uses the same backlinks endpoint but aggregates results by domain

### Request Format
```json
{
  "0": {
    "target": "example.com",
    "limit": 10000,
    "mode": "as_is",
    "filters": ["dofollow", "=", true],
    "order_by": ["domain_from_rank,desc"]
  }
}
```

### Response Processing
- Backend groups backlinks by `domain_from` to create unique referring domains list
- Sorted by domain rank (descending)

---

## 6. Bulk Pages Summary (via N8N only)

### Endpoint
- **Via N8N**: Triggered through N8N workflow (webhook: `/webhook/webhook/backlinks-bulk-page-summary`)
- **DataForSEO Endpoint**: `/backlinks/bulk_pages_summary/live` (called by N8N)

### Purpose
Get backlink summary data for multiple domains in a single request:
- Domain name
- Domain rank
- Total backlinks
- Total referring domains
- Other summary metrics

### Usage
- **When**: During bulk domain analysis (analyzing multiple domains from Namecheap auctions)
- **Method**: `N8NService.trigger_bulk_page_summary_workflow()`
- **Location**: `backend/src/services/n8n_service.py` (line 222)
- **Note**: Only available via N8N (not called directly from backend)

### Request Format (to N8N)
```json
{
  "domains": ["domain1.com", "domain2.com", "domain3.com"],
  "callback_url": "https://ngrok-url/api/v1/n8n/webhook/backlinks-bulk-page-summary",
  "request_id": "uuid",
  "type": "bulk_summary"
}
```

### Response Data Used
- Array of results, one per domain
- Each result contains: `target`, `rank`, `backlinks`, `referring_domains`, etc.

---

## Summary Table

| Endpoint | Purpose | Method | Via N8N? | When Used |
|----------|---------|--------|----------|-----------|
| `/backlinks/summary/live` | Get backlink totals | Direct or N8N | ✅ Optional | Initial analysis |
| `/backlinks/backlinks/live` | Get detailed backlinks | Direct | ❌ No | On-demand |
| `/backlinks/backlinks/task_post` | Async detailed backlinks | Direct | ❌ No | On-demand (large requests) |
| `/dataforseo_labs/google/domain_rank_overview/live` | Get domain metrics | Direct | ❌ No | Initial analysis |
| `/dataforseo_labs/google/ranked_keywords/live` | Get ranked keywords | Direct | ❌ No | On-demand |
| `/dataforseo_labs/google/ranked_keywords/task_post` | Async ranked keywords | Direct | ❌ No | On-demand (large requests) |
| `/backlinks/bulk_pages_summary/live` | Bulk domain analysis | N8N only | ✅ Yes | Bulk analysis |

---

## API Call Patterns

### Live API Calls
- Used for: Small requests (100-1000 items)
- Response: Immediate
- Cost: Higher per call
- Endpoints: `/live` suffix

### Async API Calls (POST → GET pattern)
- Used for: Large requests (up to 10,000 items)
- Pattern:
  1. POST to `/task_post` → Get `task_id`
  2. Poll `/tasks_ready` until task completes
  3. GET from `/task_get/{task_id}` → Get results
- Cost: Lower per call (70% savings)
- Endpoints: `/task_post`, `/task_get`, `/tasks_ready`

### N8N Workflow Calls
- Used for: Backlinks data (when direct API access is restricted)
- Pattern:
  1. Backend triggers N8N webhook with domain and callback URL
  2. N8N calls DataForSEO API
  3. N8N sends results back to backend webhook endpoint
- Benefits: Bypasses API restrictions, allows custom processing

---

## Cost Optimization

1. **Initial Analysis**: Only fetches summary data (backlinks summary + domain rank overview)
2. **On-Demand**: Detailed data (backlinks, keywords, referring domains) only fetched when user requests it
3. **Caching**: All data cached for 24 hours to avoid duplicate API calls
4. **Async Pattern**: Used for large requests to reduce costs (70% savings vs live)

---

## Notes

- All endpoints use DataForSEO API v3
- Base URL: `https://api.dataforseo.com/v3`
- Authentication: HTTP Basic Auth (login + password)
- Request format: Array of task objects (even for single domain)
- Response format: `{status_code: 20000, tasks: [{result: [...]}]}`


















