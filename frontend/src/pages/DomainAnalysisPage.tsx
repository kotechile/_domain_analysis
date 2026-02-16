import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  LinearProgress,
  Container,
  Stack,
  InputAdornment,
} from '@mui/material';
import {
  Search as SearchIcon,
  Store as StoreIcon,
  History as HistoryIcon,
  Bolt as BoltIcon,
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';

import { useApi } from '../services/api';
import Header from '../components/Header';

const DomainAnalysisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [domain, setDomain] = useState('');
  const [mode, setMode] = useState('dual');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const api = useApi();

  // Check for domain in URL params on mount
  useEffect(() => {
    const domainParam = searchParams.get('domain');
    const modeParam = searchParams.get('mode');
    if (domainParam) {
      setDomain(domainParam);
    }
    if (modeParam) {
      setMode(modeParam);
    }
  }, [searchParams]);

  // Analysis mutation
  const analysisMutation = useMutation({
    mutationFn: ({ domain, mode }: { domain: string; mode: string }) => api.analyzeDomain(domain, mode),
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

    analysisMutation.mutate({ domain: formattedDomain, mode });
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#0C152B' }}>
      <Header />
      <Container maxWidth="md" sx={{ py: { xs: 6, sm: 8, md: 10 } }}>
        {/* Hero Section */}
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography
            variant="h2"
            component="h1"
            gutterBottom
            sx={{
              fontWeight: 700,
              mb: 3,
              fontSize: { xs: '2.5rem', sm: '3rem', md: '3.5rem' },
              lineHeight: 1.2,
            }}
          >
            <Box component="span" sx={{ color: '#FFFFFF' }}>
              Invest in the{' '}
            </Box>
            <Box component="span" sx={{ color: '#66CCFF' }}>
              Perfect{' '}
            </Box>
            <Box component="span" sx={{ color: '#00C892' }}>
              Domain
            </Box>
          </Typography>
          <Typography
            variant="body1"
            sx={{
              maxWidth: 600,
              mx: 'auto',
              mb: 6,
              lineHeight: 1.7,
              fontSize: '1.125rem',
              color: '#FFFFFF',
              opacity: 0.9,
            }}
          >
            Deep-informed purchase analysis powered by AI. Evaluate brandability, SEO potential, and market value in seconds.
          </Typography>
        </Box>

        {/* Main Analysis Form */}
        <Box sx={{ maxWidth: 700, mx: 'auto' }}>
          <form onSubmit={handleSubmit}>
            <Stack spacing={3}>
              {/* Search Input with Inline Analyze Button */}
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  placeholder="Enter domain name (e.g. example.com)..."
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  disabled={analysisMutation.isPending}
                  error={!!error}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon sx={{ color: '#9E9E9E' }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      borderRadius: '12px',
                      color: '#FFFFFF',
                      fontSize: '1rem',
                      '& fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                      },
                      '&:hover fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#2962FF',
                      },
                      '& input::placeholder': {
                        color: '#9E9E9E',
                        opacity: 1,
                      },
                    },
                  }}
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={analysisMutation.isPending || !domain.trim()}
                  sx={{
                    minWidth: 120,
                    backgroundColor: mode === 'legacy' ? '#FFB300' : '#2962FF',
                    color: '#FFFFFF',
                    borderRadius: '12px',
                    fontSize: '1rem',
                    fontWeight: 600,
                    px: 3,
                    '&:hover': {
                      backgroundColor: mode === 'legacy' ? '#FFA000' : '#1E4ED8',
                    },
                    '&:disabled': {
                      backgroundColor: mode === 'legacy' ? 'rgba(255, 179, 0, 0.5)' : 'rgba(41, 98, 255, 0.5)',
                    },
                  }}
                  startIcon={analysisMutation.isPending ? <CircularProgress size={18} color="inherit" /> : (mode === 'legacy' ? <BoltIcon /> : null)}
                >
                  {analysisMutation.isPending ? 'Analyzing...' : (mode === 'legacy' ? 'Quick Summary' : 'Deep Analysis')}
                </Button>
              </Box>

              {error && (
                <Typography variant="body2" sx={{ color: '#FF5252', textAlign: 'center' }}>
                  {error}
                </Typography>
              )}

              {/* Action Buttons */}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="center" sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<StoreIcon />}
                  onClick={() => navigate('/marketplace')}
                  sx={{
                    color: '#FFFFFF',
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    borderRadius: '12px',
                    px: 3,
                    py: 1.25,
                    textTransform: 'none',
                    fontSize: '0.9375rem',
                    '&:hover': {
                      borderColor: 'rgba(255, 255, 255, 0.4)',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    },
                  }}
                >
                  Browse Marketplace
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<HistoryIcon />}
                  onClick={() => navigate('/reports')}
                  sx={{
                    color: '#FFFFFF',
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    borderRadius: '12px',
                    px: 3,
                    py: 1.25,
                    textTransform: 'none',
                    fontSize: '0.9375rem',
                    '&:hover': {
                      borderColor: 'rgba(255, 255, 255, 0.4)',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    },
                  }}
                >
                  Analysis History
                </Button>
              </Stack>
            </Stack>
          </form>

          {analysisMutation.isPending && (
            <Box sx={{ mt: 4 }}>
              <LinearProgress
                sx={{
                  borderRadius: 1,
                  height: 6,
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: '#2962FF',
                  },
                }}
              />
              <Typography variant="body2" sx={{ mt: 2, textAlign: 'center', color: '#FFFFFF', opacity: 0.8 }}>
                Starting analysis...
              </Typography>
            </Box>
          )}
        </Box>
      </Container>
    </Box>
  );
};

export default DomainAnalysisPage;
