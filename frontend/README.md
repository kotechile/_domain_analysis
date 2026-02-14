# Domain Scout - Frontend

A modern React frontend for Domain Scout, providing a comprehensive interface for domain SEO analysis with real-time data visualization and AI-powered insights.

## Features

- **Domain Analysis**: Submit domains for comprehensive SEO analysis
- **Real-time Progress**: Live updates during analysis processing
- **Interactive Reports**: Detailed reports with sortable tables and visualizations
- **AI Insights**: LLM-powered analysis with highlights and recommendations
- **Responsive Design**: Mobile-friendly interface with Material-UI components
- **Data Export**: Export capabilities for reports and data

## Technology Stack

- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI) v5
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Data Tables**: TanStack Table
- **Styling**: Emotion (CSS-in-JS)

## Quick Start

### Prerequisites

- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm start
   ```

The application will be available at `http://localhost:3000`

### Environment Configuration

Create a `.env` file in the frontend directory:

```bash
# API Configuration
REACT_APP_API_URL=http://localhost:8000/api/v1

# Optional: Enable debug mode
REACT_APP_DEBUG=false
```

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues
- `npm run format` - Format code with Prettier

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Header.tsx      # Navigation header
│   ├── ReportSummary.tsx
│   ├── KeywordsTable.tsx
│   ├── BacklinksTable.tsx
│   └── LLMAnalysis.tsx
├── pages/              # Page components
│   ├── DomainAnalysisPage.tsx
│   ├── ReportPage.tsx
│   └── ReportsListPage.tsx
├── services/           # API and external services
│   └── api.tsx         # API client and types
├── utils/              # Utility functions
├── App.tsx             # Main application component
└── index.tsx           # Application entry point
```

## Key Components

### DomainAnalysisPage
- Main landing page with domain input form
- System health status display
- Feature overview cards
- Real-time analysis progress

### ReportPage
- Complete domain analysis report display
- Tabbed interface for different data views
- Interactive data tables
- AI analysis visualization

### ReportsListPage
- List of all analysis reports
- Search and pagination
- Report management actions
- Status indicators

## API Integration

The frontend communicates with the backend through a centralized API service:

```typescript
// Example usage
const api = useApi();
const { data, isLoading, error } = useQuery({
  queryKey: ['report', domain],
  queryFn: () => api.getReport(domain),
});
```

### Key API Methods

- `analyzeDomain(domain)` - Start domain analysis
- `getReport(domain)` - Get analysis report
- `listReports()` - List all reports
- `getKeywords(domain)` - Get keywords data
- `getBacklinks(domain)` - Get backlinks data

## Data Visualization

### Keywords Table
- Sortable columns for rank, volume, CPC
- Search functionality
- Competition level indicators
- Pagination support

### Backlinks Table
- Domain authority indicators
- Anchor text display
- Date tracking
- External link actions

### AI Analysis
- Strengths and weaknesses highlights
- Suggested content niches
- Investment analysis table
- Confidence scoring

## Responsive Design

The application is fully responsive with breakpoints:
- **Mobile**: < 600px
- **Tablet**: 600px - 960px
- **Desktop**: > 960px

## Performance Optimizations

- **Code Splitting**: Lazy loading of components
- **Query Caching**: TanStack Query for efficient data caching
- **Memoization**: React.memo for component optimization
- **Virtual Scrolling**: For large data tables
- **Image Optimization**: Lazy loading and compression

## Accessibility

- **ARIA Labels**: Proper labeling for screen readers
- **Keyboard Navigation**: Full keyboard support
- **Color Contrast**: WCAG compliant color schemes
- **Focus Management**: Proper focus handling

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development Guidelines

### Code Style
- TypeScript strict mode
- ESLint with React hooks rules
- Prettier for code formatting
- Consistent naming conventions

### Component Guidelines
- Functional components with hooks
- Props interface definitions
- Error boundary implementation
- Loading state handling

### State Management
- Local state with useState/useReducer
- Server state with TanStack Query
- Form state with controlled components
- URL state with React Router

## Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watch
```

## Building for Production

```bash
# Build the application
npm run build

# Serve the built application
npx serve -s build
```

## Deployment

The application can be deployed to any static hosting service:

- **Vercel**: `vercel --prod`
- **Netlify**: Connect to Git repository
- **AWS S3**: Upload build folder
- **Docker**: Use nginx to serve static files

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify backend is running on correct port
   - Check CORS configuration
   - Verify API URL in environment variables

2. **Build Errors**
   - Clear node_modules and reinstall
   - Check TypeScript errors
   - Verify all dependencies are installed

3. **Performance Issues**
   - Check for memory leaks in useEffect
   - Optimize re-renders with useMemo/useCallback
   - Implement proper loading states

## Contributing

1. Follow the established code style
2. Write tests for new components
3. Update documentation as needed
4. Test across different browsers
5. Ensure responsive design works

## License

This project is part of the Domain Analysis System and follows the same license terms.
