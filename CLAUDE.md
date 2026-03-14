# Domain Analysis System (Scout) - Project Guide

## Overview

**Scout** is a comprehensive domain analysis and investment platform that helps users discover, evaluate, and invest in premium domains. The platform aggregates data from multiple domain marketplaces (GoDaddy, Namecheap, NameSilo), analyzes SEO metrics, backlink profiles, and provides AI-powered investment recommendations.

**Live URL**: https://scout.buildomain.com

---

## Architecture

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Angular 19 (standalone components, TypeScript) |
| **Backend** | Python 3.10 + FastAPI + Uvicorn |
| **Database** | Supabase (PostgreSQL with JSONB) |
| **Cache** | Redis 7 (Alpine) |
| **AI/LLM** | Google Gemini API |
| **SEO Data** | DataForSEO API |
| **Hosting** | Coolify (Docker Compose deployment) |
| **Proxy** | Traefik (via Coolify) |

### Repository Structure

```
_domain_analysis/
├── backend/                    # FastAPI Python backend
│   ├── src/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── api/routes/        # API endpoints (analysis, reports, auctions, etc.)
│   │   ├── services/          # Business logic (database, cache, external APIs)
│   │   ├── models/            # Pydantic models
│   │   └── utils/             # Configuration, utilities
│   ├── Dockerfile             # Python 3.10 slim-bookworm
│   ├── requirements.txt       # Python dependencies
│   └── supabase_migrations/   # Database schema migrations
│
├── frontend/                  # Angular 19 frontend
│   ├── src/app/
│   │   ├── pages/             # Domain analysis, marketplace, reports, billing
│   │   ├── components/        # Shared UI components (sidebar, header, etc.)
│   │   ├── services/          # API service, Supabase service, theme service
│   │   └── interceptors/      # Auth interceptor
│   ├── Dockerfile             # Multi-stage Node.js + nginx
│   ├── nginx.conf.template    # Runtime config substitution
│   └── docker-entrypoint.sh   # Environment variable injection
│
├── docker-compose.yml         # Production deployment config
└── README.md                  # General documentation
```

---

## Core Features

### 1. Domain Analysis
- **Single Domain Analysis**: Enter any domain for comprehensive SEO analysis
- **Real-time Processing**: Live progress updates during analysis
- **AI-Powered Insights**: Gemini LLM generates investment recommendations
- **Historical Data**: Wayback Machine integration for domain history

### 2. Marketplace Aggregation
- **Multi-Source**: Aggregates auctions from GoDaddy, Namecheap, NameSilo
- **Smart Filtering**: Automatic junk removal (gibberish, hyphens, low-tier TLDs)
- **Scoring Engine**: Ranks domains by Age (40%), Word Commonality (30%), Commercial Intent (30%)
- **Bulk Upload**: CSV upload support for analyzing thousands of domains

### 3. Report Generation
- **SEO Metrics**: Domain rating, organic traffic, referring domains, backlinks
- **Keyword Research**: Top organic keywords with search volume
- **Backlink Analysis**: Detailed referring domain analysis
- **Investment Memo**: Structured advantages/disadvantages with supporting metrics

### 4. Credit System
- **Usage-Based**: Credits consumed per analysis
- **Tiered Pricing**: Different credit costs for different analysis types
- **Tracking**: Real-time credit balance and usage history

### 5. N8N Integration
- **Workflow Automation**: N8N handles complex data processing pipelines
- **Webhook Callbacks**: Async processing for bulk operations
- **Data Transformation**: Automated data cleaning and enrichment

---

## API Structure

### Main Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `POST /api/v1/analyze` | Start domain analysis |
| `GET /api/v1/reports/{domain}` | Get complete report |
| `GET /api/v1/auctions` | List auction domains |
| `POST /api/v1/bulk-analysis` | Bulk domain upload |
| `GET /api/v1/credits` | Credit balance |
| `POST /api/v1/n8n/webhook/*` | N8N webhook handlers |

### Authentication
- **Method**: Supabase Auth with JWT tokens
- **Storage**: HttpOnly cookies (handled by Supabase client)
- **Providers**: Google OAuth (configured)

---

## Deployment

### Platform: Coolify

The application is deployed via **Coolify** using Docker Compose:

1. **Git Integration**: Coolify pulls from `kotechile/_domain_analysis` repo
2. **Build Process**:
   - Backend: Python 3.10 Docker image
   - Frontend: Multi-stage Node.js build → nginx:alpine
3. **Networking**: Uses external `coolify` network for Traefik integration
4. **SSL**: Automatic Let's Encrypt certificates via Traefik labels

### Environment Variables (Coolify)

#### Required Secrets
```bash
# Supabase (Self-hosted at sbdomain.buildomain.com)
SUPABASE_URL=https://sbdomain.buildomain.com
SUPABASE_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
SUPABASE_VERIFY_SSL=false

# DataForSEO
DATAFORSEO_LOGIN=<login>
DATAFORSEO_PASSWORD=<password>

# Google Gemini
GEMINI_API_KEY=<api-key>

# Security
SECRET_KEY=<random-hex-32>
```

#### Frontend Build Args
```bash
REACT_APP_API_URL=/api/v1
REACT_APP_SUPABASE_URL=${SUPABASE_URL}
REACT_APP_SUPABASE_ANON_KEY=${SUPABASE_KEY}
REACT_APP_URL=https://scout.buildomain.com
```

---

## Development

### Local Setup

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Create .env file (see .env.example)
uvicorn src.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
ng serve --port 4200
```

### Key Dependencies

**Backend:**
- FastAPI + Uvicorn (web framework)
- Supabase-py (database client)
- Redis-py (cache client)
- httpx (HTTP client for external APIs)
- structlog (structured logging)
- spacy + en_core_web_sm (NLP for domain scoring)

**Frontend:**
- Angular 19 (standalone components)
- @supabase/supabase-js (auth client)
- Tailwind CSS (styling)
- Lucide Angular (icons)

---

## Database Schema

### Key Tables

**reports**: Stores analysis results
- `domain_name` (PK), `status`, `data_for_seo_metrics` (JSONB)
- `wayback_machine_summary`, `llm_analysis`, `created_at`

**raw_data_cache**: Caches external API responses
- `domain_name`, `api_source`, `json_data`, `expires_at`

**auctions**: Domain auction listings
- `domain`, `price`, `auction_end_time`, `source` (godaddy/namesilo/namecheap)
- `total_meaning_score`, `is_preferred`, `is_premium`

**credits**: User credit tracking
- `user_id`, `balance`, `total_used`, `last_updated`

---

## Common Tasks

### Adding a New API Endpoint
1. Create route file in `backend/src/api/routes/`
2. Add router to `backend/src/main.py`
3. Add corresponding service logic in `backend/src/services/`

### Adding a New Frontend Page
1. Create component in `frontend/src/app/pages/`
2. Add route to `frontend/src/app/app.routes.ts`
3. Add sidebar link in `frontend/src/app/components/sidebar/sidebar.ts`

### Database Migrations
- Apply via Supabase Dashboard SQL Editor
- Store migration files in `backend/supabase_migrations/`

### Deploying Changes
1. Commit and push to GitHub
2. Coolify auto-deploys (or manual trigger in dashboard)
3. Check logs in Coolify if issues occur

---

## Troubleshooting

### Common Issues

**502 Bad Gateway (nginx)**
- Check backend is running: `docker logs <backend-container>`
- Verify `API_BACKEND_URL` in frontend environment

**Supabase Auth Errors**
- Check `SUPABASE_KEY` and `SUPABASE_SERVICE_ROLE_KEY` are correct
- Verify `SUPABASE_URL` matches the project
- Ensure `SUPABASE_VERIFY_SSL=false` for self-hosted

**Frontend Build Failures**
- Check Node.js version (should be 18+)
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`

**N8N Webhook Timeouts**
- Check N8N service is running
- Verify webhook URLs in environment variables
- Check network connectivity between services

---

## External Services

### DataForSEO
- **Purpose**: SEO metrics, backlinks, keyword data
- **Rate Limits**: Varies by endpoint
- **Documentation**: https://docs.dataforseo.com/

### Google Gemini
- **Purpose**: AI-powered analysis and recommendations
- **Model**: gemini-1.5-flash (configurable)
- **Rate Limits**: 60 requests/minute (free tier)

### Wayback Machine
- **Purpose**: Historical domain snapshots
- **Endpoint**: http://web.archive.org/cdx/search/cdx

---

## Security Considerations

- **CORS**: Configured for `scout.buildomain.com` and `n8n.giniloh.com`
- **RLS**: Row Level Security enabled on all Supabase tables
- **Secrets**: Never commit `.env` files (use Coolify environment variables)
- **Rate Limiting**: 60 requests/minute per IP (configurable)

---

## Future Enhancements

- [ ] Google Sheets export integration
- [ ] Advanced filtering (saved filters)
- [ ] Report scheduling and automation
- [ ] Mobile application
- [ ] API rate limiting dashboard
- [ ] White-label solutions

---

## Contact & Support

- **Repository**: https://github.com/kotechile/_domain_analysis
- **Deployment**: Coolify Dashboard (coolify.giniloh.com)
- **Monitoring**: Check Coolify logs and Traefik dashboard

---

*Last Updated: March 2026*
