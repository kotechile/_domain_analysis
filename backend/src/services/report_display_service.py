"""
Helpers for building lightweight report-detail display payloads.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_keyword_item(item: Dict[str, Any]) -> Dict[str, Any]:
    keyword_data = item.get("keyword_data", {})
    keyword_info = keyword_data.get("keyword_info", {})
    keyword_properties = keyword_data.get("keyword_properties", {})
    serp_item = item.get("ranked_serp_element", {}).get("serp_item", {})

    return {
        "keyword": item.get("keyword") or keyword_data.get("keyword", ""),
        "position": item.get("position")
        or item.get("rank")
        or serp_item.get("rank_absolute")
        or item.get("rank_absolute")
        or 0,
        "search_volume": item.get("search_volume")
        or keyword_info.get("search_volume")
        or 0,
        "cpc": item.get("cpc") if item.get("cpc") is not None else keyword_info.get("cpc", 0),
        "difficulty": item.get("difficulty")
        or item.get("keyword_difficulty")
        or keyword_properties.get("keyword_difficulty")
        or 0,
        "competition": item.get("competition")
        if item.get("competition") is not None
        else keyword_info.get("competition", 0),
        "competition_level": item.get("competition_level")
        or keyword_info.get("competition_level", ""),
        "ranking_url": item.get("ranking_url") or item.get("url") or serp_item.get("url", ""),
        "title": item.get("title") or serp_item.get("title", ""),
        "description": item.get("description") or serp_item.get("description", ""),
        "etv": item.get("etv") if item.get("etv") is not None else serp_item.get("etv", 0),
    }


def shape_keyword_items(raw_keywords: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [normalize_keyword_item(item) for item in (raw_keywords or [])]


def build_keywords_display(raw_keywords: Optional[List[Dict[str, Any]]], limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    items = raw_keywords or []
    shaped_items = shape_keyword_items(items[offset:offset + limit])

    return {
        "total_count": len(items),
        "items": shaped_items,
    }


def normalize_backlink_item(item: Dict[str, Any]) -> Dict[str, Any]:
    url_from = item.get("source_url") or item.get("url_from") or item.get("url", "")
    source_domain = item.get("domain_name_source") or item.get("domain_from") or item.get("domain", "")

    if not source_domain and url_from:
        try:
            source_domain = urlparse(url_from).netloc
        except Exception:
            source_domain = ""

    return {
        "domain": source_domain,
        "domain_rank": _coerce_int(item.get("dr", item.get("domain_from_rank", item.get("domain_rank", 0)))),
        "anchor_text": item.get("anchor_text") or item.get("anchor", ""),
        "backlinks_count": _coerce_int(item.get("links_count", item.get("backlinks_count", 1)), 1),
        "url_from": url_from,
        "url_to": item.get("href") or item.get("url_to") or item.get("target", ""),
        "link_type": item.get("type", item.get("link_type", "")),
        "link_attributes": item.get("attributes", item.get("link_attributes", "")),
        "first_seen": item.get("first_seen", ""),
        "last_seen": item.get("last_seen", ""),
        "backlink_spam_score": _coerce_int(item.get("backlink_spam_score", 0)),
    }


def shape_backlink_items(raw_backlinks: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [normalize_backlink_item(item) for item in (raw_backlinks or [])]


def build_backlinks_display(raw_backlinks: Optional[List[Dict[str, Any]]], limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    items = raw_backlinks or []
    shaped_items = shape_backlink_items(items[offset:offset + limit])

    return {
        "total_count": len(items),
        "items": shaped_items,
    }


def build_referring_domains_display(
    raw_referring_domains: Optional[List[Dict[str, Any]]],
    raw_backlinks: Optional[List[Dict[str, Any]]],
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    items = raw_referring_domains or []

    if not items and raw_backlinks:
        derived_domains: Dict[str, Dict[str, Any]] = {}
        for item in raw_backlinks:
            normalized_backlink = normalize_backlink_item(item)
            domain = normalized_backlink.get("domain") or ""
            if not domain:
                continue

            if domain not in derived_domains:
                derived_domains[domain] = {
                    "domain": domain,
                    "domain_rank": _coerce_int(normalized_backlink.get("domain_rank", 0)),
                    "anchor_text": normalized_backlink.get("anchor_text", ""),
                    "backlinks_count": 0,
                    "first_seen": normalized_backlink.get("first_seen", ""),
                    "last_seen": normalized_backlink.get("last_seen", ""),
                }

            derived_domains[domain]["backlinks_count"] += _coerce_int(
                normalized_backlink.get("backlinks_count", 1),
                1,
            )

            if not derived_domains[domain]["first_seen"]:
                derived_domains[domain]["first_seen"] = normalized_backlink.get("first_seen", "")
            if normalized_backlink.get("last_seen"):
                derived_domains[domain]["last_seen"] = normalized_backlink.get("last_seen", "")

        items = sorted(
            derived_domains.values(),
            key=lambda entry: (
                _coerce_int(entry.get("domain_rank", 0)),
                _coerce_int(entry.get("backlinks_count", 0)),
            ),
            reverse=True,
        )

    shaped_items = shape_referring_domain_items(items[offset:offset + limit])

    return {
        "total_count": len(items),
        "items": shaped_items,
    }


def normalize_referring_domain_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "domain": item.get("referring_domain") or item.get("domain") or item.get("domain_from", ""),
        "domain_rank": _coerce_int(item.get("dr", item.get("domain_rank", item.get("domain_from_rank", 0)))),
        "anchor_text": item.get("anchor_text", item.get("anchor", "")),
        "backlinks_count": _coerce_int(item.get("backlinks_count", item.get("links_count", 0))),
        "first_seen": item.get("first_seen", ""),
        "last_seen": item.get("last_seen", ""),
    }


def shape_referring_domain_items(raw_referring_domains: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [normalize_referring_domain_item(item) for item in (raw_referring_domains or [])]


def build_display_payload(
    keywords_data: Optional[Dict[str, Any]] = None,
    backlinks_data: Optional[Dict[str, Any]] = None,
    referring_domains_data: Optional[Dict[str, Any]] = None,
    keywords_limit: int = 100,
    backlinks_limit: int = 100,
) -> Dict[str, Any]:
    raw_keywords = (keywords_data or {}).get("items", [])
    raw_backlinks = (backlinks_data or {}).get("items", [])
    raw_referring_domains = (referring_domains_data or {}).get("items", [])

    return {
        "keywords": build_keywords_display(raw_keywords, keywords_limit),
        "backlinks": build_backlinks_display(raw_backlinks, backlinks_limit),
        "referring_domains": build_referring_domains_display(
            raw_referring_domains,
            raw_backlinks,
            backlinks_limit,
        ),
    }
