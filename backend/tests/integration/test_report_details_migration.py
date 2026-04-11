import pathlib
import sys

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from src.api.routes import reports as reports_routes
from src.api.routes.reports import get_report_details, _hydrate_report_response
from src.models.domain_analysis import DetailedAnalysisData, DetailedDataType, DataForSEOMetrics, LLMAnalysis


def make_report():
    return SimpleNamespace(detailed_data_available={"keywords": True, "backlinks": True, "referring_domains": True})


@pytest.mark.asyncio
async def test_report_details_falls_back_to_jsonb_and_preserves_keywords_shape(patch_owned_report):
    patch_owned_report.get_detailed_items.side_effect = [
        {"items": [], "total_count": 0},
    ]
    patch_owned_report.get_detailed_data.return_value = DetailedAnalysisData(
        domain_name="example.com",
        data_type=DetailedDataType.KEYWORDS,
        json_data={
            "items": [
                {
                    "keyword_data": {
                        "keyword": "test keyword",
                        "keyword_info": {"search_volume": 1200, "cpc": 3.5},
                        "keyword_properties": {"keyword_difficulty": 42},
                    },
                    "ranked_serp_element": {"serp_item": {"rank_absolute": 7, "url": "https://example.com/page"}},
                }
            ]
        },
    )

    result = await get_report_details(
        "example.com",
        keywords_limit=25,
        backlinks_limit=25,
        keywords_offset=0,
        backlinks_offset=0,
        sections="keywords",
        current_user={"id": "user-1"},
    )

    assert result["keywords"]["total_count"] == 1
    assert result["keywords"]["items"][0]["keyword"] == "test keyword"
    assert result["keywords"]["items"][0]["position"] == 7
    assert result["keywords"]["items"][0]["search_volume"] == 1200
    assert result["keywords"]["items"][0]["ranking_url"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_report_details_shapes_relational_backlink_rows(patch_owned_report):
    patch_owned_report.get_detailed_items.side_effect = [
        {
            "items": [
                {
                    "domain_name_source": "source.example",
                    "dr": 61,
                    "anchor": "anchor text",
                    "source_url": "https://source.example/post",
                    "href": "https://target.example/",
                }
            ],
            "total_count": 1,
        }
    ]

    result = await get_report_details(
        "example.com",
        keywords_limit=25,
        backlinks_limit=25,
        keywords_offset=0,
        backlinks_offset=0,
        sections="backlinks",
        current_user={"id": "user-1"},
    )

    assert result["backlinks"]["total_count"] == 1
    assert result["backlinks"]["items"][0]["domain"] == "source.example"
    assert result["backlinks"]["items"][0]["domain_rank"] == 61
    assert result["backlinks"]["items"][0]["anchor_text"] == "anchor text"
    assert result["backlinks"]["items"][0]["url_from"] == "https://source.example/post"
    assert result["backlinks"]["items"][0]["url_to"] == "https://target.example/"


@pytest.mark.asyncio
async def test_report_details_derives_backlink_domain_from_source_url_when_relational_row_is_sparse(patch_owned_report):
    patch_owned_report.get_detailed_items.side_effect = [
        {
            "items": [
                {
                    "source_url": "https://sparse.example/post",
                    "anchor": "anchor text",
                    "href": "https://target.example/",
                }
            ],
            "total_count": 1,
        }
    ]

    result = await get_report_details(
        "example.com",
        keywords_limit=25,
        backlinks_limit=25,
        keywords_offset=0,
        backlinks_offset=0,
        sections="backlinks",
        current_user={"id": "user-1"},
    )

    assert result["backlinks"]["total_count"] == 1
    assert result["backlinks"]["items"][0]["domain"] == "sparse.example"
    assert result["backlinks"]["items"][0]["url_from"] == "https://sparse.example/post"
    assert result["backlinks"]["items"][0]["anchor_text"] == "anchor text"


@pytest.mark.asyncio
async def test_report_details_uses_backlinks_json_to_derive_referring_domains_when_section_missing(patch_owned_report):
    patch_owned_report.get_derived_referring_domains.side_effect = Exception("missing derived rows")
    patch_owned_report.get_detailed_data.side_effect = [
        DetailedAnalysisData(
            domain_name="example.com",
            data_type=DetailedDataType.BACKLINKS,
            json_data={
                "items": [
                    {
                        "domain_from": "ref.example",
                        "domain_from_rank": 55,
                        "anchor": "brand anchor",
                        "links_count": 2,
                    }
                ]
            },
        ),
        None,
    ]

    result = await get_report_details(
        "example.com",
        keywords_limit=25,
        backlinks_limit=25,
        keywords_offset=0,
        backlinks_offset=0,
        sections="referring_domains",
        current_user={"id": "user-1"},
    )

    assert result["referring_domains"]["total_count"] == 1
    assert result["referring_domains"]["items"][0]["domain"] == "ref.example"
    assert result["referring_domains"]["items"][0]["domain_rank"] == 55
    assert result["referring_domains"]["items"][0]["backlinks_count"] == 2


@pytest.mark.asyncio
async def test_report_details_prefers_derived_referring_domains_from_backlinks(patch_owned_report):
    patch_owned_report.get_derived_referring_domains.return_value = {
        "items": [
            {
                "referring_domain": "derived.example",
                "dr": 72,
                "backlinks_count": 4,
            }
        ],
        "total_count": 1,
    }

    result = await get_report_details(
        "example.com",
        keywords_limit=25,
        backlinks_limit=25,
        keywords_offset=0,
        backlinks_offset=0,
        sections="referring_domains",
        current_user={"id": "user-1"},
    )

    assert result["referring_domains"]["total_count"] == 1
    assert result["referring_domains"]["items"][0]["domain"] == "derived.example"
    assert result["referring_domains"]["items"][0]["domain_rank"] == 72
    assert result["referring_domains"]["items"][0]["backlinks_count"] == 4


@pytest.mark.asyncio
async def test_hydrate_report_response_derives_referring_domains_and_refreshes_stale_ai():
    db = AsyncMock()
    db.get_detailed_items.side_effect = [
        {"items": [{"keyword": "calla lily care"}], "total_count": 1},
        {
            "items": [
                {
                    "source_url": "https://www.citychickens.co.uk/post-1",
                    "href": "https://callalilyguide.com/growing",
                    "anchor": "seeds",
                    "dr": 55,
                }
            ],
            "total_count": 100,
        },
        {"items": [], "total_count": 0},
        {
            "items": [
                {
                    "source_url": "https://www.citychickens.co.uk/post-1",
                    "href": "https://callalilyguide.com/growing",
                    "anchor": "seeds",
                    "dr": 55,
                },
                {
                    "source_url": "https://blog.example.org/post-2",
                    "href": "https://callalilyguide.com/growing",
                    "anchor": "calla lily",
                    "dr": 42,
                },
            ],
            "total_count": 100,
        },
        {
            "items": [{"keyword": "calla lily care"}],
            "total_count": 90,
        },
    ]
    db.get_derived_referring_domains.return_value = {"items": [], "total_count": 0}
    db.get_raw_data.return_value = {}
    db.save_report = AsyncMock()

    report = SimpleNamespace(
        domain_name="callalilyguide.com",
        status="completed",
        data_for_seo_metrics=DataForSEOMetrics(
            domain_rating_dr=7.1,
            organic_traffic_est=372.354,
            total_backlinks=0,
            total_referring_domains=0,
            total_keywords=0,
        ),
        llm_analysis=LLMAnalysis(
            buy_recommendation={
                "recommendation": "CAUTION",
                "confidence": 0.01,
                "reasoning": "Domain currently has 0 links and 0 referring domains.",
                "risk_level": "high",
                "potential_value": "low",
            },
            summary="This domain lacks a backlink profile (0 links).",
            confidence_score=0.01,
        ),
        detailed_data_available={},
        display_payload=None,
        historical_data=None,
        wayback_machine_summary=None,
    )

    hydrated = await _hydrate_report_response(db, report)

    assert hydrated.data_for_seo_metrics.total_backlinks == 100
    assert hydrated.data_for_seo_metrics.total_referring_domains == 2
    assert hydrated.llm_analysis.summary == (
        "Domain analysis for callalilyguide.com - NO-BUY recommendation based on 100 backlinks and 1 keywords"
    )
    assert hydrated.llm_analysis.confidence_score == 0.7
    db.save_report.assert_awaited_once()


@pytest.fixture(autouse=True)
def patch_owned_report(monkeypatch):
    db = AsyncMock()

    async def fake_get_owned_report_or_404(domain, current_user):
        return db, make_report()

    monkeypatch.setattr(reports_routes, "_get_owned_report_or_404", fake_get_owned_report_or_404)
    return db
