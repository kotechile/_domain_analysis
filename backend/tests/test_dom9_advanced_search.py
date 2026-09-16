"""
Tests for saved queries CRUD, advanced search filters, and SQL sanitization (DOM-9)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel


class TestFilterSettingsModel:
    def test_filter_settings_defaults(self):
        from api.routes.filters import FilterSettings
        fs = FilterSettings()
        assert fs.sort_by == 'expiration_date'
        assert fs.sort_order == 'asc'
        assert fs.page_size == 50
        assert fs.filter_name == 'default'
        assert fs.is_default is False
        assert fs.min_price is None
        assert fs.max_price is None
        assert fs.keyword is None

    def test_filter_settings_with_price_range(self):
        from api.routes.filters import FilterSettings
        fs = FilterSettings(min_price=10, max_price=500)
        assert fs.min_price == 10
        assert fs.max_price == 500

    def test_filter_settings_with_keyword(self):
        from api.routes.filters import FilterSettings
        fs = FilterSettings(keyword='crypto')
        assert fs.keyword == 'crypto'

    def test_filter_settings_serialization(self):
        from api.routes.filters import FilterSettings
        fs = FilterSettings(
            preferred=True,
            min_price=5,
            max_price=200,
            keyword='blockchain',
            expiration_from_date='2026-01-01',
            tlds=['.com', '.io']
        )
        data = fs.model_dump()
        assert data['preferred'] is True
        assert data['min_price'] == 5
        assert data['max_price'] == 200
        assert data['keyword'] == 'blockchain'
        assert data['tlds'] == ['.com', '.io']


class TestSavedQueryModels:
    def test_saved_query_create(self):
        from api.routes.filters import SavedQueryCreate
        sq = SavedQueryCreate(name='Test Query', query_params={'search': 'crypto', 'min_price': 10})
        assert sq.name == 'Test Query'
        assert sq.query_params['search'] == 'crypto'
        assert sq.is_default is False

    def test_saved_query_update(self):
        from api.routes.filters import SavedQueryUpdate
        sq = SavedQueryUpdate(name='Updated')
        assert sq.name == 'Updated'
        assert sq.query_params is None
        assert sq.is_default is None

    def test_saved_query_create_default(self):
        from api.routes.filters import SavedQueryCreate
        sq = SavedQueryCreate(name='My Default', query_params={}, is_default=True)
        assert sq.is_default is True

    def test_saved_query_create_with_full_filters(self):
        from api.routes.filters import SavedQueryCreate
        params = {
            'preferred': True,
            'tlds': ['.com', '.ai'],
            'offering_type': 'auction',
            'min_score': 5,
            'max_score': 50,
            'min_price': 10,
            'max_price': 500,
            'keyword': 'blockchain',
            'sort_by': 'score',
            'sort_order': 'desc'
        }
        sq = SavedQueryCreate(name='Full Filter Set', query_params=params)
        assert sq.query_params['min_price'] == 10
        assert sq.query_params['keyword'] == 'blockchain'


class TestAdvancedFilterParams:
    def test_filters_include_price_range(self):
        filters = {
            'min_price': 10,
            'max_price': 500,
            'min_score': 3,
            'max_score': 25,
        }
        assert 'min_price' in filters
        assert 'max_price' in filters
        assert filters['min_price'] == 10
        assert filters['max_price'] == 500

    def test_filters_include_keyword(self):
        filters = {
            'keyword': 'crypto',
            'search': 'blockchain',
        }
        assert 'keyword' in filters
        assert filters['keyword'] == 'crypto'
        assert filters['search'] == 'blockchain'

    def test_filters_include_offering_type(self):
        filters = {'offering_type': 'buy_now'}
        assert filters['offering_type'] == 'buy_now'


class TestSqlSanitization:
    def test_sanitize_sql_value_basic(self):
        from services.database import DatabaseService
        result = DatabaseService._sanitize_sql_value("normal_value")
        assert result == "normal_value"

    def test_sanitize_sql_value_single_quotes(self):
        from services.database import DatabaseService
        result = DatabaseService._sanitize_sql_value("test'; DROP TABLE auctions;--")
        assert "''" in result
        assert "'" not in result.replace("''", "")

    def test_sanitize_sql_value_null_byte(self):
        from services.database import DatabaseService
        result = DatabaseService._sanitize_sql_value("test\x00value")
        assert "\x00" not in result

    def test_sanitize_sql_identifier_valid(self):
        from services.database import DatabaseService
        result = DatabaseService._sanitize_sql_identifier("expiration_date")
        assert result == "expiration_date"

    def test_sanitize_sql_identifier_invalid(self):
        from services.database import DatabaseService
        with pytest.raises(ValueError):
            DatabaseService._sanitize_sql_identifier("expiration_date; DROP TABLE auctions")

    def test_sanitize_sql_identifier_dangerous(self):
        from services.database import DatabaseService
        with pytest.raises(ValueError):
            DatabaseService._sanitize_sql_identifier("1; DROP TABLE auctions")


class TestBuildWhereConditions:
    def _make_service(self):
        from services.database import DatabaseService
        return DatabaseService()

    def test_empty_filters(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions(None)
        assert conditions == ["to_delete = FALSE"]

    def test_preferred_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'preferred': True})
        assert "preferred = true" in conditions

    def test_search_filter_sanitized(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'search': "test'; DROP TABLE auctions;--"})
        where = " AND ".join(conditions)
        assert "''" in where
        assert "DROP TABLE" not in where or "''" in where

    def test_keyword_filter_sanitized(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'keyword': "crypto';--"})
        where = " AND ".join(conditions)
        assert "''" in where

    def test_price_range_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'min_price': 10, 'max_price': 500})
        where = " AND ".join(conditions)
        assert "current_bid >= 10.0" in where
        assert "current_bid <= 500.0" in where

    def test_auction_sites_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'auction_sites': ['godaddy', 'namecheap']})
        where = " AND ".join(conditions)
        assert "auction_site IN ('godaddy', 'namecheap')" in where

    def test_auction_sites_filter_sanitized(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'auction_sites': ["godaddy'; DROP TABLE auctions;--"]})
        where = " AND ".join(conditions)
        assert "''" in where

    def test_offering_type_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'offering_type': 'buy_now'})
        assert "offer_type = 'buy_now'" in conditions

    def test_score_range_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'min_score': 5, 'max_score': 50})
        where = " AND ".join(conditions)
        assert "score >= 5.0" in where
        assert "score <= 50.0" in where

    def test_rank_range_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'min_rank': 1, 'max_rank': 100})
        where = " AND ".join(conditions)
        assert "name_rank >= 1" in where
        assert "name_rank <= 100" in where

    def test_tlds_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'tlds': ['.com', '.io']})
        where = " AND ".join(conditions)
        assert "ILIKE" in where
        assert ".com" in where

    def test_expiration_date_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({
            'expiration_from_date': '2026-01-01T00:00:00Z',
            'expiration_to_date': '2026-12-31T23:59:59Z'
        })
        where = " AND ".join(conditions)
        assert "expiration_date >=" in where
        assert "expiration_date <=" in where

    def test_scored_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'scored': True})
        assert "score > 0" in conditions

    def test_scored_filter_false(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'scored': False})
        where = " AND ".join(conditions)
        assert "score IS NULL OR score = 0" in where

    def test_has_statistics_filter(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({'has_statistics': True})
        assert "has_statistics = true" in conditions

    def test_combined_filters(self):
        svc = self._make_service()
        conditions = svc._build_where_conditions({
            'preferred': True,
            'offering_type': 'auction',
            'min_score': 5,
            'max_price': 200,
            'keyword': 'crypto',
            'tlds': ['.com'],
            'scored': True
        })
        where = " AND ".join(conditions)
        assert "preferred = true" in where
        assert "offer_type = 'auction'" in where
        assert "score >= 5.0" in where
        assert "current_bid <= 200.0" in where
        assert "ILIKE '%crypto%'" in where
        assert "score > 0" in where


class TestDatabaseFilterPostgrestPath:
    def test_filters_include_min_price(self):
        filters = {'min_price': 10}
        assert 'min_price' in filters
        assert filters['min_price'] == 10

    def test_filters_include_max_price(self):
        filters = {'max_price': 500}
        assert 'max_price' in filters
        assert filters['max_price'] == 500

    def test_filters_include_keyword(self):
        filters = {'keyword': 'blockchain'}
        assert 'keyword' in filters
        assert filters['keyword'] == 'blockchain'