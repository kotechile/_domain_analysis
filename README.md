# Get Domain

A comprehensive domain analysis platform that provides detailed SEO insights, backlink analysis, keyword research, and AI-powered recommendations for domain investment decisions.

## 🚀 Features

### Core Analysis
- **SEO Metrics**: Domain rating, organic traffic, referring domains, and backlinks
- **Keyword Research**: Top organic keywords with search volume and competition data
- **Backlink Analysis**: Detailed referring domain analysis with authority scores
- **Historical Data**: Wayback Machine integration for domain history assessment

### AI-Powered Insights
- **Smart Analysis**: LLM-generated highlights of strengths and weaknesses
- **Niche Suggestions**: AI-recommended content niches based on existing SEO foundation
- **Investment Analysis**: Structured advantages/disadvantages with supporting metrics
- **Risk Assessment**: Historical domain usage analysis and reputation evaluation

### User Experience
- **Real-time Processing**: Live progress updates during analysis
- **Interactive Reports**: Sortable tables, searchable data, and visual indicators
- **Responsive Design**: Mobile-friendly interface with modern UI components
- **Export Capabilities**: Data export and report sharing functionality

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with Uvicorn ASGI server
- **Database**: Supabase (PostgreSQL) with JSONB storage
- **Cache**: Redis for performance optimization
- **APIs**: DataForSEO, Wayback Machine, Gemini LLM
- **Authentication**: Supabase Auth with Row Level Security

### Frontend (React)
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI) v5
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router v6
- **Data Tables**: TanStack Table for advanced table features

## 📋 Prerequisites

- Python 3.10+
- Node.js 16+
- Redis server
- Supabase account
- DataForSEO account
- Gemini API key

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd domain-analysis-system
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your API keys and configuration

# Start the backend
python src/main.py
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env

# Start the frontend
npm start
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

### Required Environment Variables

#### Backend (.env)
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

#### Frontend (.env)
```bash
REACT_APP_API_URL=http://localhost:8000/api/v1
```

## 📊 API Endpoints

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

## 🗄️ Database Schema

### Reports Table
```sql
CREATE TABLE reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL UNIQUE,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    data_for_seo_metrics JSONB,
    wayback_machine_summary JSONB,
    llm_analysis JSONB,
    raw_data_links JSONB,
    processing_time_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Raw Data Cache Table
```sql
CREATE TABLE raw_data_cache (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    api_source VARCHAR(50) NOT NULL,
    json_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(domain_name, api_source)
);
```

## 🔄 Data Flow

1. **User Input**: Domain submitted via frontend form
2. **Validation**: Domain format validation and sanitization
3. **Data Collection**: Parallel API calls to DataForSEO and Wayback Machine
4. **Caching**: Raw data stored in Redis and Supabase
5. **AI Analysis**: LLM processes data and generates insights
6. **Storage**: Complete report saved to Supabase
7. **Response**: User receives analysis results with real-time updates

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
pytest --cov=src  # With coverage
```

### Frontend Tests
```bash
cd frontend
npm test
npm test -- --coverage  # With coverage
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Production Considerations
- Use environment-specific configuration
- Set up proper logging and monitoring
- Configure rate limiting and security headers
- Use a production WSGI server (Gunicorn with Uvicorn workers)
- Set up health checks and auto-scaling

## 📈 Performance

### Backend Performance
- **Analysis Time**: ≤15 seconds for 90% of requests
- **Concurrency**: Supports ≥10 concurrent analyses
- **Caching**: 30-day cache for external API data
- **Database**: Optimized queries with proper indexing

### Frontend Performance
- **Code Splitting**: Lazy loading of components
- **Query Caching**: Efficient data caching with TanStack Query
- **Virtual Scrolling**: For large data tables
- **Responsive Design**: Mobile-first approach

## 🔒 Security

- **Authentication**: Supabase Auth with JWT tokens
- **Authorization**: Row Level Security (RLS) on all tables
- **Input Validation**: Comprehensive validation on all inputs
- **Rate Limiting**: API rate limiting to prevent abuse
- **CORS**: Properly configured cross-origin resource sharing
- **Secrets Management**: Environment variables for sensitive data

## 📚 Documentation

- **API Documentation**: Auto-generated OpenAPI/Swagger docs at `/docs`
- **Code Documentation**: Comprehensive docstrings and type hints
- **User Guide**: Built-in help and tooltips
- **Architecture**: Detailed system architecture documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the established code style (Black for Python, Prettier for TypeScript)
- Write tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API documentation at `/docs`

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Core domain analysis functionality
- ✅ AI-powered insights
- ✅ Real-time progress tracking
- ✅ Responsive web interface

### Phase 2 (Planned)
- [ ] Google Sheets export integration
- [ ] Bulk domain analysis
- [ ] Advanced filtering and search
- [ ] Report scheduling and automation

### Phase 3 (Future)
- [ ] Mobile application
- [ ] API rate limiting dashboard
- [ ] Advanced analytics and reporting
- [ ] White-label solutions

## 🙏 Acknowledgments

- **DataForSEO** for comprehensive SEO data
- **Wayback Machine** for historical domain data
- **Google Gemini** for AI-powered analysis
- **Supabase** for database and authentication
- **Material-UI** for beautiful UI components
- **FastAPI** for high-performance API framework
