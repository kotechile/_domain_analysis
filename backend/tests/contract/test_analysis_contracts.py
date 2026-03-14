"""
Contract tests for analysis API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.main import app
from models.domain_analysis import AnalysisMode, AnalysisPhase, AsyncTaskStatus


class TestAnalysisContracts:
    """Contract tests for analysis endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    @patch('src.services.analysis_service.AnalysisService')
    def test_analyze_domain_legacy_mode(self, mock_analysis_service):
        """Test domain analysis in legacy mode"""
        # Mock service response
        mock_service = AsyncMock()
        mock_service.analyze_domain.return_value = {
            "success": True,
            "message": "Analysis completed",
            "report_id": "test-report-123",
            "analysis_mode": "legacy"
        }
        mock_analysis_service.return_value = mock_service
        
        response = self.client.post(
            "/api/v2/analyze",
            json={
                "domain": "example.com",
                "mode": "legacy"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["analysis_mode"] == "legacy"
    
    @patch('src.services.analysis_service.AnalysisService')
    def test_analyze_domain_async_mode(self, mock_analysis_service):
        """Test domain analysis in async mode"""
        # Mock service response
        mock_service = AsyncMock()
        mock_service.analyze_domain.return_value = {
            "success": True,
            "message": "Analysis started",
            "report_id": "test-report-456",
            "analysis_mode": "async",
            "estimated_completion_time": 120,
            "progress_url": "/api/v2/analyze/example.com/progress"
        }
        mock_analysis_service.return_value = mock_service
        
        response = self.client.post(
            "/api/v2/analyze",
            json={
                "domain": "example.com",
                "mode": "async"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["analysis_mode"] == "async"
        assert "progress_url" in data
    
    @patch('src.services.analysis_service.AnalysisService')
    def test_get_analysis_status(self, mock_analysis_service):
        """Test getting analysis status"""
        # Mock service response
        mock_service = AsyncMock()
        mock_service.get_analysis_status.return_value = {
            "success": True,
            "message": "Status retrieved",
            "report_id": "test-report-123",
            "status": "in_progress",
            "analysis_phase": "detailed",
            "analysis_mode": "async",
            "detailed_data_available": {
                "backlinks": True,
                "keywords": False,
                "referring_domains": False
            },
            "progress": {
                "status": "in_progress",
                "phase": "detailed",
                "progress_percentage": 60,
                "estimated_time_remaining": 30,
                "current_operation": "Collecting backlinks"
            }
        }
        mock_analysis_service.return_value = mock_service
        
        response = self.client.get(
            "/api/v2/analyze/example.com/status?mode=async"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "in_progress"
        assert data["analysis_phase"] == "detailed"
        assert "progress" in data
    
    @patch('src.services.analysis_service.AnalysisService')
    def test_get_detailed_data(self, mock_analysis_service):
        """Test getting detailed analysis data"""
        # Mock service response
        mock_service = AsyncMock()
        mock_service.get_detailed_data.return_value = {
            "success": True,
            "data": {
                "items": [
                    {
                        "url_from": "https://example.com/page1",
                        "domain_from": "example.com",
                        "domain_from_rank": 85,
                        "anchor": "example link",
                        "first_seen": "2023-01-01",
                        "quality_score": 8.5
                    }
                ],
                "total_count": 1
            },
            "metadata": {
                "domain": "example.com",
                "data_type": "backlinks",
                "created_at": "2023-01-01T00:00:00Z",
                "data_freshness": "fresh",
                "record_count": 1
            }
        }
        mock_analysis_service.return_value = mock_service
        
        response = self.client.get(
            "/api/v2/analyze/example.com/detailed/backlinks"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data
        assert data["metadata"]["data_type"] == "backlinks"
    
    @patch('src.services.analysis_service.AnalysisService')
    def test_get_progress(self, mock_analysis_service):
        """Test getting analysis progress"""
        # Mock service response
        mock_service = AsyncMock()
        mock_service.get_progress.return_value = {
            "success": True,
            "progress": {
                "status": "in_progress",
                "phase": "detailed",
                "progress_percentage": 75,
                "estimated_time_remaining": 15,
                "current_operation": "Processing keywords",
                "completed_operations": [
                    "Essential data collection",
                    "Backlinks collection"
                ]
            }
        }
        mock_analysis_service.return_value = mock_service
        
        response = self.client.get(
            "/api/v2/analyze/example.com/progress"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "progress" in data
        assert data["progress"]["status"] == "in_progress"
        assert data["progress"]["progress_percentage"] == 75
    
    @patch('src.services.analysis_service.AnalysisService')
    def test_manual_refresh(self, mock_analysis_service):
        """Test manual refresh functionality"""
        # Mock service response
        mock_service = AsyncMock()
        mock_service.refresh_analysis.return_value = {
            "success": True,
            "message": "Refresh initiated",
            "refresh_id": "refresh-123"
        }
        mock_analysis_service.return_value = mock_service
        
        response = self.client.post(
            "/api/v2/analyze/example.com/refresh",
            json={
                "data_types": ["backlinks", "keywords"],
                "force": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "refresh_id" in data
    
    def test_analyze_domain_validation(self):
        """Test domain validation"""
        # Test invalid domain
        response = self.client.post(
            "/api/v2/analyze",
            json={
                "domain": "invalid",
                "mode": "legacy"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_domain_missing_domain(self):
        """Test missing domain parameter"""
        response = self.client.post(
            "/api/v2/analyze",
            json={
                "mode": "legacy"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_detailed_data_invalid_type(self):
        """Test invalid data type"""
        response = self.client.get(
            "/api/v2/analyze/example.com/detailed/invalid_type"
        )
        
        assert response.status_code == 422  # Validation error





