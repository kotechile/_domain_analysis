import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CssBaseline from '@mui/material/CssBaseline';
import { ApiProvider } from './services/api';
import ErrorBoundary from './components/ErrorBoundary';
import { ThemeContextProvider } from './theme/ThemeContext';

import DomainAnalysisPage from './pages/DomainAnalysisPage';
import ReportsListPage from './pages/ReportsListPage';
import ReportPage from './pages/ReportPage';
import AuctionsPage from './pages/AuctionsPage';
import DomainsTablePage from './pages/DomainsTablePage';
import Auth from './pages/Auth';
import AuthCallback from './pages/AuthCallback';
import ProtectedRoute from './components/ProtectedRoute';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ApiProvider>
          <ThemeContextProvider>
            <CssBaseline />
            <Router future={{ v7_relativeSplatPath: true }}>
              <Routes>
                {/* Public Routes */}
                <Route path="/login" element={<Auth />} />
                <Route path="/auth/callback" element={<AuthCallback />} />

                {/* Protected Routes */}
                <Route element={<ProtectedRoute />}>
                  <Route path="/" element={<DomainAnalysisPage />} />
                  <Route path="/reports" element={<ReportsListPage />} />
                  <Route path="/reports/:domain" element={<ReportPage />} />
                  <Route path="/auctions" element={<AuctionsPage />} />
                  <Route path="/marketplace" element={<DomainsTablePage />} />
                </Route>
              </Routes>
            </Router>
          </ThemeContextProvider>
        </ApiProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;