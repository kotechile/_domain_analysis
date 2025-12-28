# Quickstart Guide: Domain Analysis Workflow Improvements

## Overview

This guide provides a quick start for implementing the enhanced domain analysis workflow with dual-mode operation support, async DataForSEO integration, and comprehensive backlink quality assessment.

## Key Features

- **Dual-Mode Operation**: Support both legacy and async analysis patterns
- **Cost Optimization**: 70%+ reduction in DataForSEO API costs through async pattern
- **Enhanced AI Analysis**: Comprehensive backlink quality assessment with detailed data
- **Progress Tracking**: Real-time progress indicators with estimated time remaining
- **Intelligent Caching**: 24-hour TTL with manual refresh options
- **Fail-Fast Error Handling**: Immediate error feedback with graceful degradation

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend       │    │  External APIs  │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Progress    │ │◄───┤ │ Analysis     │ │◄───┤ │ DataForSEO  │ │
│ │ Indicators  │ │    │ │ Service      │ │    │ │ Async API   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Dual-Mode   │ │◄───┤ │ DataForSEO   │ │◄───┤ │ Wayback     │ │
│ │ UI Controls │ │    │ │ Async Service│ │    │ │ Machine     │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Enhanced    │ │◄───┤ │ Enhanced     │ │◄───┤ │ Gemini LLM  │ │
│ │ Data Tables │ │    │ │ Database     │ │    │ │ Analysis    │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Implementation Phases

### Phase 1: Database Schema Enhancement

1. **Create new tables**:
   ```sql
   -- Run migration script
   psql -d your_database -f supabase_migrations/003_create_detailed_data_tables.sql
   ```

2. **Verify schema**:
   ```sql
   -- Check new tables exist
   \dt detailed_analysis_data
   \dt async_tasks
   \dt analysis_mode_config
   ```

### Phase 2: Backend Implementation

1. **Install dependencies**:
   ```bash
   pip install httpx asyncio structlog
   ```

2. **Create async DataForSEO service**:
   ```python
   # backend/src/services/dataforseo_async.py
   from services.dataforseo_async import DataForSEOAsyncService
   
   async_service = DataForSEOAsyncService()
   result = await async_service.get_detailed_backlinks_async("example.com")
   ```

3. **Update analysis service for dual-mode**:
   ```python
   # backend/src/services/analysis_service.py
   class AnalysisService:
       def __init__(self):
           self.legacy_service = DataForSEOService()  # Existing
           self.async_service = DataForSEOAsyncService()  # New
           
       async def analyze_domain(self, domain: str, mode: str = "dual"):
           if mode == "legacy":
               return await self._legacy_analysis(domain)
           elif mode == "async":
               return await self._async_analysis(domain)
           else:  # dual mode
               return await self._dual_mode_analysis(domain)
   ```

### Phase 3: API Endpoints

1. **Add new endpoints**:
   ```python
   # backend/src/api/routes/analysis.py
   
   @router.post("/analyze")
   async def analyze_domain(request: AnalysisRequest):
       # Support both legacy and async modes
       pass
   
   @router.get("/analyze/{domain}/progress")
   async def get_progress(domain: str):
       # Real-time progress tracking
       pass
   
   @router.get("/analyze/{domain}/detailed/{data_type}")
   async def get_detailed_data(domain: str, data_type: str):
       # Detailed data retrieval
       pass
   ```

2. **Test endpoints**:
   ```bash
   # Start analysis
   curl -X POST "http://localhost:8000/api/v2/analyze" \
        -H "Content-Type: application/json" \
        -d '{"domain": "example.com", "mode": "async"}'
   
   # Check progress
   curl "http://localhost:8000/api/v2/analyze/example.com/progress"
   
   # Get detailed data
   curl "http://localhost:8000/api/v2/analyze/example.com/detailed/backlinks"
   ```

### Phase 4: Frontend Implementation

1. **Add progress indicator component**:
   ```typescript
   // frontend/src/components/ProgressIndicator.tsx
   interface ProgressIndicatorProps {
     progress: ProgressInfo;
     onCancel?: () => void;
   }
   
   export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
     progress,
     onCancel
   }) => {
     return (
       <Box>
         <LinearProgress 
           variant="determinate" 
           value={progress.progress_percentage} 
         />
         <Typography>
           {progress.current_operation} ({progress.progress_percentage}%)
         </Typography>
         {progress.estimated_time_remaining && (
           <Typography variant="caption">
             Estimated time remaining: {progress.estimated_time_remaining}s
           </Typography>
         )}
       </Box>
     );
   };
   ```

2. **Update analysis page for dual-mode**:
   ```typescript
   // frontend/src/pages/DomainAnalysisPage.tsx
   const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("dual");
   const [progress, setProgress] = useState<ProgressInfo | null>(null);
   
   const startAnalysis = async (domain: string) => {
     const response = await api.analyzeDomain(domain, analysisMode);
     if (response.analysis_mode === "async") {
       // Start progress polling
       pollProgress(domain);
     }
   };
   ```

3. **Enhanced data display**:
   ```typescript
   // frontend/src/components/BacklinksTable.tsx
   interface BacklinksTableProps {
     data: DetailedBacklinkData[];
     showQualityMetrics: boolean;
   }
   
   export const BacklinksTable: React.FC<BacklinksTableProps> = ({
     data,
     showQualityMetrics
   }) => {
     return (
       <Table>
         <TableHead>
           <TableRow>
             <TableCell>Domain</TableCell>
             <TableCell>Domain Rank</TableCell>
             {showQualityMetrics && <TableCell>Quality Score</TableCell>}
             <TableCell>Anchor Text</TableCell>
             <TableCell>First Seen</TableCell>
           </TableRow>
         </TableHead>
         <TableBody>
           {data.map((backlink) => (
             <TableRow key={backlink.id}>
               <TableCell>{backlink.domain_from}</TableCell>
               <TableCell>{backlink.domain_from_rank}</TableCell>
               {showQualityMetrics && (
                 <TableCell>
                   <Chip 
                     label={backlink.quality_score} 
                     color={getQualityColor(backlink.quality_score)}
                   />
                 </TableCell>
               )}
               <TableCell>{backlink.anchor}</TableCell>
               <TableCell>{backlink.first_seen}</TableCell>
             </TableRow>
           ))}
         </TableBody>
       </Table>
     );
   };
   ```

## Configuration

### Environment Variables

```bash
# DataForSEO Configuration
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
DATAFORSEO_API_URL=https://api.dataforseo.com/v3

# Cache Configuration
CACHE_TTL_HOURS=24
MANUAL_REFRESH_ENABLED=true

# Async Configuration
ASYNC_POLL_INTERVAL=2
ASYNC_MAX_ATTEMPTS=30
ASYNC_TIMEOUT=30

# Progress Tracking
PROGRESS_INDICATORS_ENABLED=true
```

### Database Configuration

```sql
-- Set up RLS policies
CREATE POLICY "Public can read detailed data" ON detailed_analysis_data 
FOR SELECT USING (true);

CREATE POLICY "Service role can manage detailed data" ON detailed_analysis_data 
FOR ALL USING (auth.role() = 'service_role');

-- Create indexes for performance
CREATE INDEX idx_detailed_data_domain_type ON detailed_analysis_data(domain_name, data_type);
CREATE INDEX idx_async_tasks_status ON async_tasks(status);
```

## Testing

### Unit Tests

```python
# backend/tests/unit/test_dataforseo_async.py
import pytest
from unittest.mock import AsyncMock, patch
from services.dataforseo_async import DataForSEOAsyncService

@pytest.mark.asyncio
async def test_get_detailed_backlinks_async():
    service = DataForSEOAsyncService()
    
    with patch.object(service, '_execute_async_task') as mock_execute:
        mock_execute.return_value = {"items": [{"url": "test.com"}]}
        
        result = await service.get_detailed_backlinks_async("example.com")
        
        assert result is not None
        assert "items" in result
        mock_execute.assert_called_once()
```

### Integration Tests

```python
# backend/tests/integration/test_dual_mode.py
@pytest.mark.asyncio
async def test_dual_mode_analysis():
    service = AnalysisService()
    
    # Test legacy mode
    legacy_result = await service.analyze_domain("example.com", "legacy")
    assert legacy_result.analysis_mode == "legacy"
    
    # Test async mode
    async_result = await service.analyze_domain("example.com", "async")
    assert async_result.analysis_mode == "async"
    
    # Test dual mode
    dual_result = await service.analyze_domain("example.com", "dual")
    assert dual_result.analysis_mode in ["legacy", "async"]
```

### Frontend Tests

```typescript
// frontend/src/components/__tests__/ProgressIndicator.test.tsx
import { render, screen } from '@testing-library/react';
import { ProgressIndicator } from '../ProgressIndicator';

describe('ProgressIndicator', () => {
  it('displays progress percentage', () => {
    const progress = {
      status: 'in_progress',
      phase: 'detailed',
      progress_percentage: 50,
      current_operation: 'Collecting backlinks'
    };
    
    render(<ProgressIndicator progress={progress} />);
    
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('Collecting backlinks')).toBeInTheDocument();
  });
});
```

## Monitoring and Observability

### Logging

```python
# Structured logging for async operations
logger.info("Async task started", 
           domain=domain, 
           task_type=task_type, 
           task_id=task_id)

logger.info("Async task completed", 
           domain=domain, 
           task_type=task_type, 
           duration=duration)
```

### Metrics

```python
# Track key metrics
metrics.increment('analysis.started', tags={'mode': analysis_mode})
metrics.timing('analysis.duration', duration, tags={'mode': analysis_mode})
metrics.gauge('cache.hit_rate', cache_hit_rate)
```

### Health Checks

```python
# Health check endpoint
@router.get("/health/async")
async def async_health_check():
    return {
        "status": "healthy",
        "async_service": await async_service.health_check(),
        "cache_status": await cache_service.health_check()
    }
```

## Troubleshooting

### Common Issues

1. **Async task timeout**:
   - Check DataForSEO API status
   - Verify network connectivity
   - Increase timeout configuration

2. **Cache miss rate high**:
   - Check TTL configuration
   - Verify cache cleanup is running
   - Monitor storage usage

3. **Progress not updating**:
   - Check WebSocket connection
   - Verify polling interval
   - Check browser console for errors

### Debug Commands

```bash
# Check async task status
curl "http://localhost:8000/api/v2/analyze/example.com/progress"

# Check cache status
curl "http://localhost:8000/api/v2/analyze/example.com/cache-status"

# Force refresh
curl -X POST "http://localhost:8000/api/v2/analyze/example.com/refresh"
```

## Migration Guide

### From Legacy to Dual-Mode

1. **Deploy new code** with dual-mode support
2. **Configure mode preference** to "dual"
3. **Test with small subset** of domains
4. **Monitor performance** and error rates
5. **Gradually increase** async mode usage
6. **Switch to async-only** when confident

### Rollback Plan

1. **Set mode preference** to "legacy"
2. **Disable async endpoints** if needed
3. **Revert to previous** code version
4. **Verify functionality** is restored

## Performance Optimization

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_detailed_data_created_at 
ON detailed_analysis_data(created_at);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM detailed_analysis_data 
WHERE domain_name = 'example.com' AND data_type = 'backlinks';
```

### Caching Optimization

```python
# Implement cache warming
async def warm_cache(domain: str):
    """Pre-populate cache with frequently accessed data"""
    await async_service.get_detailed_backlinks_async(domain)
    await async_service.get_detailed_keywords_async(domain)
```

## Security Considerations

### API Security

```python
# Rate limiting for async operations
@limiter.limit("10 per minute")
async def start_async_analysis(request: AnalysisRequest):
    pass

# Input validation
@validate_request(AnalysisRequest)
async def analyze_domain(request: AnalysisRequest):
    pass
```

### Data Protection

```python
# Encrypt sensitive data
encrypted_data = encrypt_sensitive_data(backlink_data)

# Sanitize user inputs
sanitized_domain = sanitize_domain(domain)
```

## Support and Maintenance

### Regular Maintenance

1. **Clean expired data** (daily)
2. **Monitor API usage** (hourly)
3. **Check error rates** (continuously)
4. **Update cache TTL** (as needed)

### Monitoring Alerts

- High error rate (>5%)
- Long async task duration (>5 minutes)
- Low cache hit rate (<80%)
- API quota exceeded

This quickstart guide provides everything needed to implement the enhanced domain analysis workflow with dual-mode operation support.





