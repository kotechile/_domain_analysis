import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  LinearProgress,
  Chip,
  Grid,
  Paper,
} from '@mui/material';
import {
  Search as SearchIcon,
  Analytics as AnalyticsIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';
import { useMutation, useQuery } from '@tanstack/react-query';

import { useApi } from '../services/api';

const DomainAnalysisPage: React.FC = () => {
  const [domain, setDomain] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const api = useApi();

  // Health check query
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.getHealth(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Analysis mutation
  const analysisMutation = useMutation({
    mutationFn: (domain: string) => api.analyzeDomain(domain),
    onSuccess: (data) => {
      if (data.success) {
        navigate(`/reports/${domain}`);
      } else {
        setError(data.message);
      }
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to start analysis');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!domain.trim()) {
      setError('Please enter a domain name');
      return;
    }

    const formattedDomain = api.formatDomain(domain);
    if (!api.validateDomain(formattedDomain)) {
      setError('Please enter a valid domain name (e.g., example.com)');
      return;
    }

    analysisMutation.mutate(formattedDomain);
  };

  const getServiceStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'unhealthy':
        return 'error';
      default:
        return 'warning';
    }
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Domain Analysis System
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          Comprehensive SEO analysis with backlinks, keywords, and AI-powered insights
        </Typography>
      </Box>

      {/* System Status */}
      {healthData && (
        <Paper sx={{ p: 2, mb: 4, bgcolor: 'background.paper' }}>
          <Typography variant="h6" gutterBottom>
            System Status
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={healthData.status}
                  color={healthData.status === 'healthy' ? 'success' : 'warning'}
                  size="small"
                />
                <Typography variant="body2">Overall</Typography>
              </Box>
            </Grid>
            {Object.entries(healthData.services).map(([service, status]) => (
              <Grid item xs={12} sm={6} md={3} key={service}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={status}
                    color={getServiceStatusColor(status) as any}
                    size="small"
                  />
                  <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                    {service.replace('_', ' ')}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* Main Analysis Form */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
              <TextField
                fullWidth
                label="Domain Name"
                placeholder="Enter domain (e.g., example.com)"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                disabled={analysisMutation.isPending}
                error={!!error}
                helperText={error || 'Enter a domain name to analyze its SEO performance'}
                InputProps={{
                  startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                }}
              />
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={analysisMutation.isPending || !domain.trim()}
                sx={{ minWidth: 120, height: 56 }}
              >
                {analysisMutation.isPending ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Analyze'
                )}
              </Button>
            </Box>
          </form>

          {analysisMutation.isPending && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Starting analysis...
              </Typography>
              <LinearProgress />
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Features */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <AnalyticsIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                SEO Metrics
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Get comprehensive SEO data including domain rating, organic traffic, backlinks,
                and keyword rankings from DataForSEO.
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <SpeedIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Fast Analysis
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Complete domain analysis in under 15 seconds with parallel data collection and
                intelligent caching.
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <SecurityIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                AI Insights
              </Typography>
              <Typography variant="body2" color="text.secondary">
                AI-powered analysis with highlights, niche suggestions, and historical risk
                assessment using advanced LLM technology.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Reports Link */}
      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Button
          variant="outlined"
          onClick={() => navigate('/reports')}
          sx={{ minWidth: 200 }}
        >
          View Recent Reports
        </Button>
      </Box>
    </Box>
  );
};

export default DomainAnalysisPage;
