<!--
Sync Impact Report:
Version change: 0.0.0 → 1.0.0
Modified principles: N/A (new constitution)
Added sections: API-First Architecture, Data Quality & Caching, Performance & Scalability, Security & Compliance
Removed sections: N/A
Templates requiring updates: ✅ plan-template.md, ✅ spec-template.md, ✅ tasks-template.md
Follow-up TODOs: None
-->

# Domain Analysis System Constitution

## Core Principles

### I. API-First Architecture (NON-NEGOTIABLE)
Every system component MUST expose functionality via well-defined APIs; FastAPI backend serves as the single source of truth for all domain analysis operations; Frontend MUST consume backend APIs exclusively; All external integrations (DataForSEO, Wayback Machine, LLM) MUST be abstracted behind service layers; API contracts MUST be versioned and backward-compatible.

### II. Data Quality & Caching (NON-NEGOTIABLE)
All external API responses MUST be validated and sanitized before storage; Raw data MUST be cached in Supabase for 30 days to minimize API costs; Data quality checks MUST be implemented for all external API integrations; Invalid or corrupted data MUST be flagged and excluded from analysis; Cache invalidation MUST be handled automatically based on data freshness requirements.

### III. Test-First Development (NON-NEGOTIABLE)
TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced; All API endpoints MUST have contract tests; All external service integrations MUST have integration tests; All LLM analysis functions MUST have unit tests with mock data; Test coverage MUST exceed 80% for all critical paths.

### IV. Performance & Scalability
Analysis completion MUST be ≤15 seconds for 90% of requests; System MUST support ≥10 concurrent analyses without degradation; Database queries MUST be optimized with proper indexing; API responses MUST be paginated for large datasets; Caching strategy MUST be implemented at multiple levels (API, database, frontend); Async/await patterns MUST be used for all I/O operations.

### V. Security & Compliance
All API keys MUST be stored as environment variables; User authentication MUST be implemented via Supabase Auth; Row Level Security (RLS) MUST be enabled on all database tables; Input validation MUST be implemented for all user inputs; Rate limiting MUST be implemented for all external API calls; All user data MUST be encrypted in transit and at rest.

## Technology Stack Requirements

### Backend Architecture
- **Framework**: FastAPI with Uvicorn ASGI server
- **Language**: Python 3.10+
- **Database**: Supabase (PostgreSQL) with official Python SDK
- **External APIs**: DataForSEO, Wayback Machine, Gemini API
- **Caching**: Supabase database with 30-day TTL
- **Authentication**: Supabase Auth with RLS

### Frontend Architecture
- **Framework**: React with TypeScript
- **State Management**: React Query for server state
- **UI Components**: Modern component library (Material-UI or similar)
- **Data Tables**: TanStack Table for sortable/searchable tables
- **Export**: Google Sheets API integration

### Data Integration
- **SEO Data**: DataForSEO API (Backlinks, Keywords, Domain Analytics)
- **Historical Data**: Wayback Machine CDX API
- **Analysis**: Gemini API for LLM-powered report generation
- **Storage**: Supabase PostgreSQL with JSONB columns

## Development Workflow

### Code Quality Standards
- All code MUST follow PEP 8 standards (Python) and ESLint rules (TypeScript)
- API documentation MUST be auto-generated via FastAPI OpenAPI
- All functions MUST have type hints and docstrings
- Code reviews MUST verify compliance with constitution principles
- Complexity MUST be justified with clear rationale

### Testing Requirements
- Unit tests for all business logic functions
- Integration tests for all external API calls
- Contract tests for all API endpoints
- End-to-end tests for complete user journeys
- Performance tests for scalability requirements

### Deployment & Monitoring
- Environment-specific configuration management
- Structured logging for all operations
- Error tracking and alerting
- Performance monitoring and metrics
- Automated deployment pipeline

## Governance

Constitution supersedes all other practices; Amendments require documentation, approval, and migration plan; All PRs/reviews must verify compliance; Complexity must be justified; Use README.md for runtime development guidance; Regular compliance reviews every quarter.

**Version**: 1.0.0 | **Ratified**: 2025-01-18 | **Last Amended**: 2025-01-18
