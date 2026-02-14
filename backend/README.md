# Domain Scout - Backend

A FastAPI-based backend service for comprehensive domain analysis with SEO data, backlinks, and LLM-powered insights.

## Features

- **Domain Analysis**: Complete SEO analysis including backlinks, keywords, and traffic data
- **External API Integration**: DataForSEO, Wayback Machine, and Gemini LLM
- **Caching**: Redis-based caching for performance optimization
- **Database**: Supabase PostgreSQL with JSONB storage
- **Real-time Processing**: Asynchronous analysis with progress tracking
- **RESTful API**: Well-documented API with OpenAPI/Swagger docs

## Technology Stack

- **Framework**: FastAPI 0.104.1
- **Language**: Python 3.10+
- **Database**: Supabase (PostgreSQL)
- **Cache**: Redis
- **External APIs**: DataForSEO, Wayback Machine, Gemini
- **Authentication**: Supabase Auth

## Quick Start

### Prerequisites

- Python 3.10+
- Redis server
- Supabase account
- DataForSEO account
- Gemini API key

### Installation

1. **Clone and navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your actual API keys and configuration
   ```

5. **Run the application**:
   ```bash
   python src/main.py
   ```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /api/v1/health` - System health status
- `GET /api/v1/health/ready` - Readiness check
- `GET /api/v1/health/live` - Liveness check

### Domain Analysis
- `POST /api/v1/analyze` - Start domain analysis
- `GET /api/v1/analyze/{domain}` - Get analysis status
- `DELETE /api/v1/analyze/{domain}` - Cancel analysis
- `POST /api/v1/analyze/{domain}/retry` - Retry failed analysis

### Reports
- `GET /api/v1/reports/{domain}` - Get complete report
- `GET /api/v1/reports` - List all reports (paginated)
- `GET /api/v1/reports/{domain}/keywords` - Get keywords data
- `GET /api/v1/reports/{domain}/backlinks` - Get backlinks data
- `DELETE /api/v1/reports/{domain}` - Delete report

## Configuration

### Required Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# DataForSEO
DATAFORSEO_LOGIN=your-login
DATAFORSEO_PASSWORD=your-password

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Security
SECRET_KEY=your-secret-key
```

### Optional Environment Variables

```bash
# Redis (default: redis://localhost:6379)
REDIS_URL=redis://localhost:6379

# Server (default: 0.0.0.0:8000)
HOST=0.0.0.0
PORT=8000

# CORS (default: localhost:3000, localhost:3001)
ALLOWED_ORIGINS=["http://localhost:3000"]
```

## Development

### Code Quality

The project follows strict code quality standards:

- **Linting**: Black, isort, flake8
- **Type Checking**: mypy
- **Testing**: pytest with async support
- **Documentation**: Auto-generated OpenAPI docs

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_analysis.py
```

### Code Formatting

```bash
# Format code
black src/
isort src/

# Check formatting
black --check src/
isort --check-only src/
```

## Architecture

### Service Layer

- **AnalysisService**: Orchestrates the complete analysis workflow
- **DataForSEOService**: Handles SEO data collection
- **WaybackMachineService**: Manages historical data
- **LLMService**: Generates AI-powered insights
- **DatabaseService**: Manages data persistence
- **CacheService**: Handles Redis caching

### Data Flow

1. **Request**: User submits domain for analysis
2. **Data Collection**: Parallel API calls to DataForSEO and Wayback Machine
3. **Caching**: Raw data stored in Redis and Supabase
4. **Analysis**: LLM processes data and generates insights
5. **Storage**: Complete report saved to Supabase
6. **Response**: User receives analysis results

### Error Handling

- Comprehensive error logging with structured logging
- Graceful degradation when external services are unavailable
- Retry mechanisms for transient failures
- User-friendly error messages

## Deployment

### Docker

```bash
# Build image
docker build -t domain-analysis-backend .

# Run container
docker run -p 8000:8000 --env-file .env domain-analysis-backend
```

### Production Considerations

- Use environment-specific configuration
- Set up proper logging and monitoring
- Configure rate limiting and security headers
- Use a production WSGI server (Gunicorn with Uvicorn workers)
- Set up health checks and auto-scaling

## Monitoring

### Health Checks

The service provides comprehensive health checks:

- **Database connectivity**
- **External API availability**
- **Cache service status**
- **Overall system health**

### Logging

Structured JSON logging with:

- Request/response tracking
- Performance metrics
- Error details with stack traces
- External API call monitoring

## License

This project is part of the Domain Analysis System and follows the same license terms.
