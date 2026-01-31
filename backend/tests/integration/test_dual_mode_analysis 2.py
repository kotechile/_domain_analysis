"""
Integration tests for dual-mode analysis operation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.analysis_service import AnalysisService
from src.services.dataforseo_async import DataForSEOAsyncService
from src.services.external_apis import DataForSEOService
from models.domain_analysis import AnalysisMode, AnalysisPhase, AsyncTaskStatus


class TestDualModeAnalysis:
    """Integration tests for dual-mode analysis"""
    
    @pytest.fixture
    def analysis_service(self):
        """Create analysis service instance"""
        return AnalysisService()
    
    @pytest.fixture
    def mock_async_service(self):
        """Mock async DataForSEO service"""
        service = AsyncMock(spec=DataForSEOAsyncService)
        service.get_detailed_backlinks_async.return_value = {
            "items": [{"url_from": "https://example.com", "domain_from_rank": 85}],
            "total_count": 1
        }
        service.get_detailed_keywords_async.return_value = {
            "items": [{"keyword": "test keyword", "position": 5}],
            "total_count": 1
        }
        service.get_referring_domains_async.return_value = {
            "items": [{"domain_from": "example.com", "domain_from_rank": 85}],
            "total_count": 1
        }
        return service
    
    @pytest.fixture
    def mock_legacy_service(self):
        """Mock legacy DataForSEO service"""
        service = AsyncMock(spec=DataForSEOService)
        service.get_domain_rank_overview.return_value = {
            "domain_rating_dr": 85.5,
            "total_keywords": 1000,
            "organic_metrics": {"pos_1": 10, "pos_2_3": 20}
        }
        service.get_detailed_backlinks.return_value = {
            "items": [{"url_from": "https://example.com", "domain_from_rank": 85}],
            "total_count": 1
        }
        service.get_detailed_keywords.return_value = {
            "items": [{"keyword": "test keyword", "position": 5}],
            "total_count": 1
        }
        service.get_referring_domains.return_value = {
            "items": [{"domain_from": "example.com", "domain_from_rank": 85}],
            "total_count": 1
        }
        return service
    
    @pytest.mark.asyncio
    async def test_legacy_mode_analysis(self, analysis_service, mock_legacy_service):
        """Test analysis in legacy mode"""
        with patch.object(analysis_service, 'dataforseo_service', mock_legacy_service):
            result = await analysis_service.analyze_domain("example.com", "legacy")
            
            assert result is not None
            assert result.analysis_mode == AnalysisMode.LEGACY
            assert result.analysis_phase == AnalysisPhase.COMPLETED
            assert result.data_for_seo_metrics is not None
            assert result.llm_analysis is not None
    
    @pytest.mark.asyncio
    async def test_async_mode_analysis(self, analysis_service, mock_async_service):
        """Test analysis in async mode"""
        with patch.object(analysis_service, 'dataforseo_async_service', mock_async_service):
            result = await analysis_service.analyze_domain("example.com", "async")
            
            assert result is not None
            assert result.analysis_mode == AnalysisMode.ASYNC
            assert result.analysis_phase == AnalysisPhase.COMPLETED
            assert result.detailed_data_available["backlinks"] is True
            assert result.detailed_data_available["keywords"] is True
            assert result.detailed_data_available["referring_domains"] is True
    
    @pytest.mark.asyncio
    async def test_dual_mode_analysis_legacy_fallback(self, analysis_service, mock_legacy_service, mock_async_service):
        """Test dual mode with legacy fallback when async fails"""
        # Make async service fail
        mock_async_service.get_detailed_backlinks_async.return_value = None
        
        with patch.object(analysis_service, 'dataforseo_service', mock_legacy_service), \
             patch.object(analysis_service, 'dataforseo_async_service', mock_async_service):
            
            result = await analysis_service.analyze_domain("example.com", "dual")
            
            assert result is not None
            assert result.analysis_mode == AnalysisMode.LEGACY  # Should fallback to legacy
            assert result.analysis_phase == AnalysisPhase.COMPLETED
    
    @pytest.mark.asyncio
    async def test_dual_mode_analysis_async_success(self, analysis_service, mock_legacy_service, mock_async_service):
        """Test dual mode with async success"""
        with patch.object(analysis_service, 'dataforseo_service', mock_legacy_service), \
             patch.object(analysis_service, 'dataforseo_async_service', mock_async_service):
            
            result = await analysis_service.analyze_domain("example.com", "dual")
            
            assert result is not None
            assert result.analysis_mode == AnalysisMode.ASYNC  # Should use async
            assert result.analysis_phase == AnalysisPhase.COMPLETED
            assert result.detailed_data_available["backlinks"] is True
    
    @pytest.mark.asyncio
    async def test_progress_tracking_async_mode(self, analysis_service, mock_async_service):
        """Test progress tracking in async mode"""
        with patch.object(analysis_service, 'dataforseo_async_service', mock_async_service):
            # Start analysis
            result = await analysis_service.analyze_domain("example.com", "async")
            
            assert result is not None
            assert result.progress_data is not None
            assert result.progress_data.status == AsyncTaskStatus.COMPLETED
            assert result.progress_data.phase == AnalysisPhase.COMPLETED
            assert result.progress_data.progress_percentage == 100
    
    @pytest.mark.asyncio
    async def test_detailed_data_availability(self, analysis_service, mock_async_service):
        """Test detailed data availability tracking"""
        with patch.object(analysis_service, 'dataforseo_async_service', mock_async_service):
            result = await analysis_service.analyze_domain("example.com", "async")
            
            assert result is not None
            assert result.detailed_data_available["backlinks"] is True
            assert result.detailed_data_available["keywords"] is True
            assert result.detailed_data_available["referring_domains"] is True
    
    @pytest.mark.asyncio
    async def test_analysis_phase_progression(self, analysis_service, mock_legacy_service):
        """Test analysis phase progression"""
        with patch.object(analysis_service, 'dataforseo_service', mock_legacy_service):
            result = await analysis_service.analyze_domain("example.com", "legacy")
            
            assert result is not None
            assert result.analysis_phase == AnalysisPhase.COMPLETED
    
    @pytest.mark.asyncio
    async def test_error_handling_async_failure(self, analysis_service, mock_async_service):
        """Test error handling when async operations fail"""
        # Make async service raise exception
        mock_async_service.get_detailed_backlinks_async.side_effect = Exception("API Error")
        
        with patch.object(analysis_service, 'dataforseo_async_service', mock_async_service):
            result = await analysis_service.analyze_domain("example.com", "async")
            
            assert result is not None
            assert result.error_message is not None
            assert "API Error" in result.error_message
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, analysis_service, mock_legacy_service):
        """Test handling concurrent analysis requests"""
        with patch.object(analysis_service, 'dataforseo_service', mock_legacy_service):
            # Start multiple concurrent analyses
            tasks = [
                analysis_service.analyze_domain(f"example{i}.com", "legacy")
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for result in results:
                assert result is not None
                assert result.analysis_mode == AnalysisMode.LEGACY
    
    @pytest.mark.asyncio
    async def test_cache_utilization(self, analysis_service, mock_legacy_service):
        """Test cache utilization for repeated analyses"""
        with patch.object(analysis_service, 'dataforseo_service', mock_legacy_service):
            # First analysis
            result1 = await analysis_service.analyze_domain("example.com", "legacy")
            assert result1 is not None
            
            # Second analysis should use cache
            result2 = await analysis_service.analyze_domain("example.com", "legacy")
            assert result2 is not None
            
            # Should be the same domain
            assert result1.domain_name == result2.domain_name





