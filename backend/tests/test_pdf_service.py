import pathlib
import sys

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from src.services.pdf_service import PDFService


def test_generate_domain_analysis_pdf_handles_extended_sections():
    payload = {
        "analysis_timestamp": "2026-04-11T20:00:00Z",
        "generated_at": "2026-04-11T20:01:00Z",
        "processing_time_seconds": 12.3,
        "data_for_seo_metrics": {
            "domain_rating_dr": 7.1,
            "organic_traffic_est": 372354,
            "total_backlinks": 100,
            "total_referring_domains": 55,
        },
        "llm_analysis": {
            "buy_recommendation": {
                "recommendation": "CAUTION",
                "reasoning": "Strong topical relevance but mixed authority profile.",
                "risk_level": "medium",
                "potential_value": "high",
            },
            "confidence_score": 0.85,
            "summary": "Aged domain with meaningful organic visibility and a usable backlink base.",
            "valuable_assets": [
                "Established age and archive history",
                "Meaningful backlink footprint",
            ],
            "good_highlights": ["Strong niche alignment"],
            "major_concerns": ["Backlink quality is uneven"],
            "content_strategy": {
                "primary_niche": "Gardening",
                "secondary_niches": ["Flowers", "Bulbs"],
                "target_keywords": ["calla lily care", "calla lily bulbs"],
                "first_articles": ["How to grow calla lilies", "Common calla lily problems"],
            },
            "action_plan": {
                "immediate_actions": ["Preserve strongest pages"],
                "first_month": ["Refresh core content"],
                "long_term_strategy": ["Expand topical coverage"],
            },
            "pros_and_cons": [
                {
                    "type": "pro",
                    "impact": "high",
                    "description": "Existing organic visibility",
                    "example": "Traffic history remains active",
                },
                {
                    "type": "con",
                    "impact": "medium",
                    "description": "Authority concentration risk",
                    "example": "High-DR links are limited",
                },
            ],
        },
        "wayback_machine_summary": {
            "first_capture_year": 2008,
            "total_captures": 1000,
            "historical_risk_assessment": "No critical history risks detected.",
        },
        "historical_data": {
            "rank_overview": {
                "organic_traffic": [
                    {"date": "2026-01-01", "value": 120},
                    {"date": "2026-02-01", "value": 140},
                ]
            }
        },
        "backlinks": {
            "total_count": 2,
            "items": [
                {
                    "domain": "source.example",
                    "domain_rank": 61,
                    "url_from": "https://source.example/post",
                    "anchor_text": "calla lilies",
                    "url_to": "https://example.com",
                }
            ],
        },
        "referring_domains": {
            "total_count": 1,
            "items": [
                {
                    "domain": "source.example",
                    "domain_rank": 61,
                    "backlinks_count": 2,
                    "anchor_text": "calla lilies",
                    "first_seen": "2026-01-01",
                }
            ],
        },
        "keywords": {
            "total_count": 1,
            "items": [
                {
                    "keyword": "calla lily care",
                    "position": 7,
                    "search_volume": 1200,
                    "cpc": 1.25,
                    "ranking_url": "https://example.com/calla-lily-care",
                }
            ],
        },
    }

    pdf_bytes = PDFService().generate_domain_analysis_pdf("example.com", payload)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
