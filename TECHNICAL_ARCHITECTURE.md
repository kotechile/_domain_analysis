# Domain Analysis System - Technical Architecture

This document provides a technical overview of the Domain Analysis system, detailing the scoring engine, data ingestion pipeline, and external service integrations.

## 1. System Overview

The system is a multi-service platform designed to evaluate and rank domain names for investment potential. It combines traditional SEO metrics with advanced NLP-driven semantic analysis and LLM-generated insights.

## 2. The Scoring Engine

The scoring engine operates in two distinct stages to ensure both efficiency and depth.

### Stage 1: Absolute Filters (Hard Stops)
Implemented in `DomainScoringService._stage1_filter`, these filters eliminate "junk" domains before expensive analysis begins:
- **TLD Tiering**: Only allows premium extensions (defined in `TIER_1_TLDS`).
- **Lexical Complexity**: Limits domain length and excludes hyphens or excessive numbers.
- **Dictionary Recognition**: Uses tokenization (spaCy or regex) and a `word_frequency.json` database to ensure the domain consists of recognizable words. A minimum recognition ratio is required.

### Stage 2: Advanced Scoring (0-100 Scale)
Domains passing Stage 1 are assigned a **Total Meaning Score** based on three weighted components:

| Component | Weight | Description |
| :--- | :--- | :--- |
| **Age Score** | 40% | Derived from `registered_date`. 10+ years = 100 points, 5+ years = 50 points. |
| **Lexical Frequency (LFS)** | 30% | Calculated by checking tokens against a word frequency database (Rank 1 = 100 points). |
| **Semantic Value** | 30% | Combines Part-of-Speech (POS) analysis and Industry Relevance (IRS). |

**Semantic Value Details:**
- **POS Tagging (spaCy)**: Prioritizes Nouns (30 pts) and Verbs (20 pts) over Adjectives (15 pts).
- **Industry Relevance**: Checks against a curated `industry_keywords.json` of high-value commercial terms.

## 3. Deep Analysis Pipeline

Triggered on-demand, the `AnalysisService` orchestrates a four-phase workflow:

1. **Essential Data**: Fetches high-level metrics (Domain Rating, Organic Traffic, Wayback capture year).
2. **Detailed Data**: Collects deep backlink lists and keyword rankings. This phase uses **n8n workflows** for complex summary operations to keep the API responsive.
3. **Historical Data**: Retrieves 12-24 month histories for organic traffic and keyword counts.
4. **AI Analysis (Google Gemini)**: Aggregates all previous data into a prompt for Gemini, which generates a structured investment report (pros, cons, niche suggestions).

## 4. Technology Stack & Integrations

- **Backend**: FastAPI (Python 3.12+).
- **NLP**: spaCy (`en_core_web_sm`).
- **Database**: Supabase (PostgreSQL) with JSONB for flexible metrics storage.
- **Automation**: n8n for background processing and webhook handling.
- **APIs**:
    - **DataForSEO**: Real-time SEO metrics and history.
    - **Wayback Machine**: Historical archiving data.
    - **Google Gemini**: LLM for qualitative synthesis.

## 5. Deployment & Scalability

- **Async Processing**: Uses Python `asyncio` and N8N for non-blocking operations.
- **Batch Processing**: Auction marketplace data (GoDaddy, Namecheap) is loaded via a staging table and merged in chunks to handle datasets of 100k+ records without database timeouts.
