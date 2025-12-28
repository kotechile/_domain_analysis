# N8N Integration Scope

## ✅ What Uses N8N

**ONLY Backlinks Data:**

1. **Backlinks Summary** (Essential Data Phase)
   - Endpoint: `/backlinks/summary/live`
   - Purpose: Get totals (`total_backlinks`, `total_referring_domains`, `rank`)
   - N8N Workflow: `/webhook/webhook/backlinks-summary`
   - Backend Method: `trigger_backlinks_summary_workflow()`

2. **Detailed Backlinks** (Detailed Data Phase)
   - Endpoint: `/backlinks/backlinks/live` or `/backlinks/backlinks/task_post`
   - Purpose: Get individual backlink records
   - N8N Workflow: `/webhook/webhook/backlinks-details`
   - Backend Method: `trigger_backlinks_workflow()`

## ❌ What Does NOT Use N8N (Direct Backend Calls)

All other DataForSEO API calls are made **directly by the backend**:

1. **Domain Rank Overview**
   - Endpoint: `/dataforseo_labs/google/domain_rank_overview/live`
   - Purpose: Get domain ranking metrics, organic traffic estimates
   - Backend Method: `get_domain_analytics()` → Direct API call
   - **NOT backlinks-related**

2. **Keywords Data**
   - Endpoint: `/dataforseo_labs/google/serp/live` or `/dataforseo_labs/google/serp/task_post`
   - Purpose: Get organic keywords ranking data
   - Backend Method: `get_detailed_keywords()` or `get_detailed_keywords_async()`
   - **NOT backlinks-related**

3. **Referring Domains**
   - Endpoint: `/backlinks/referring_domains/live` or `/backlinks/referring_domains/task_post`
   - Purpose: Get referring domains data
   - Backend Method: `get_referring_domains()` or `get_referring_domains_async()`
   - **Note**: This is related to backlinks but is a separate endpoint, so it's called directly

## Summary

| Data Type | Uses N8N? | Reason |
|-----------|-----------|--------|
| Backlinks Summary | ✅ Yes | User's DataForSEO account only allows backlinks via N8N |
| Detailed Backlinks | ✅ Yes | User's DataForSEO account only allows backlinks via N8N |
| Domain Rank Overview | ❌ No | Not backlinks-related, direct API call |
| Keywords | ❌ No | Not backlinks-related, direct API call |
| Referring Domains | ❌ No | Separate endpoint, direct API call |

## Implementation Details

### Backend Logic

1. **Essential Data Collection** (`_collect_essential_data()`):
   - ✅ Uses N8N for backlinks summary (if `N8N_USE_FOR_SUMMARY=true`)
   - ✅ Calls DataForSEO directly for domain rank overview
   - ✅ Falls back to direct API for backlinks summary if N8N fails (but will fail if API is disabled)

2. **Detailed Data Collection** (`_collect_detailed_data()`):
   - ✅ Uses N8N for detailed backlinks (if `N8N_USE_FOR_BACKLINKS=true`)
   - ✅ Calls DataForSEO directly for keywords
   - ✅ Calls DataForSEO directly for referring domains
   - ✅ Falls back to direct API for backlinks if N8N fails (but will fail if API is disabled)

3. **Domain Analytics** (`get_domain_analytics()`):
   - ✅ Skips backlinks summary call if N8N is enabled
   - ✅ Always calls domain rank overview directly
   - ✅ Uses cached backlinks summary if available (from N8N)

## Configuration

```bash
# Enable N8N for backlinks only
N8N_ENABLED=true
N8N_USE_FOR_BACKLINKS=true      # For detailed backlinks
N8N_USE_FOR_SUMMARY=true        # For backlinks summary

# All other DataForSEO calls use direct API (no N8N config needed)
```

## Why This Architecture?

- **User's DataForSEO account**: Only allows backlinks API access through N8N
- **Other APIs**: Domain rank, keywords, referring domains are accessible directly
- **Cost efficiency**: N8N is only used where necessary (backlinks)
- **Performance**: Direct API calls are faster for non-backlinks data


















