import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Alert,
  Button,
  Paper,
  Stack,
  useTheme,
  CircularProgress,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Domain as DomainIcon,
  Link as LinkIcon,
  Search as SearchIcon,
  Schedule as ScheduleIcon,
  NewReleases as NewReleasesIcon,
  Remove as RemoveIcon,
  OpenInNew as OpenInNewIcon,
  Language as LanguageIcon,
  Public as PublicIcon,
  Warning as WarningIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

import { DomainAnalysisReport, useApi, BulkPageSummaryResult } from '../services/api';

interface ReportSummaryProps {
  report: DomainAnalysisReport;
}

const ReportSummary: React.FC<ReportSummaryProps> = ({ report }) => {
  const theme = useTheme();
  const api = useApi();
  const metrics = report.data_for_seo_metrics;
  const llmAnalysis = report.llm_analysis;
  const wayback = report.wayback_machine_summary;
  const [pageStatistics, setPageStatistics] = useState<BulkPageSummaryResult | null>(null);
  const [loadingPageStats, setLoadingPageStats] = useState(false);

  // Use page summary from report if available, otherwise try to fetch from cache
  useEffect(() => {
    // First check if it's already in the report
    if (report.backlinks_page_summary) {
      console.log('Using backlinks_page_summary from report:', report.backlinks_page_summary);
      setPageStatistics(report.backlinks_page_summary);
      setLoadingPageStats(false);
      return;
    }
    
    console.log('No backlinks_page_summary in report, fetching from cache...');

    // Otherwise, try to fetch from cache (for backward compatibility with old reports)
    const fetchPageSummary = async () => {
      try {
        setLoadingPageStats(true);
        const response = await api.getPageSummary(report.domain_name);
        
        if (response.success && response.data) {
          setPageStatistics(response.data as BulkPageSummaryResult);
        }
      } catch (error) {
        // Silently fail - page summary might not be available
        console.debug('Page summary not available for this domain:', error);
      } finally {
        setLoadingPageStats(false);
      }
    };

    fetchPageSummary();
  }, [report.domain_name, report.backlinks_page_summary, api]);

  const formatNumber = (num: number | undefined | null) => {
    if (num === undefined || num === null) return 'N/A';
    return num.toLocaleString();
  };

  const formatPercentage = (num: number | undefined | null) => {
    if (num === undefined || num === null) return 'N/A';
    return `${(num * 100).toFixed(1)}%`;
  };

  // Extract chart data from page_statistics (only if available)
  const chartData = useMemo(() => {
    if (!pageStatistics) return { tldData: [], countryData: [] };

    // Individual analysis backlinks_summary may not have these fields
    // Only show charts if the data structure matches BulkPageSummaryResult
    const tldData = (pageStatistics as any).referring_links_tld
      ? Object.entries((pageStatistics as any).referring_links_tld).map(([name, value]) => ({
          name: name || 'unknown',
          value: Number(value) || 0,
        }))
      : [];

    const countryData = (pageStatistics as any).referring_links_countries
      ? Object.entries((pageStatistics as any).referring_links_countries)
          .map(([name, value]) => ({
            name: name && name.trim() ? name : 'Unknown',
            value: Number(value) || 0,
          }))
          .filter((item) => item.value > 0) // Filter out zero values
          .sort((a, b) => b.value - a.value)
          .slice(0, 10) // Top 10 countries
      : [];

    return { tldData, countryData };
  }, [pageStatistics]);

  // Chart colors
  const CHART_COLORS = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // orange
    '#ef4444', // red
    '#8b5cf6', // purple
    '#ec4899', // pink
    '#06b6d4', // cyan
    '#84cc16', // lime
    '#f97316', // orange-600
    '#6366f1', // indigo
  ];

  const MetricItem: React.FC<{
    icon: React.ReactNode;
    label: string;
    value: string | number;
    color?: string;
  }> = ({ icon, label, value, color }) => (
    <Paper 
      variant="outlined" 
      sx={{ 
        p: 2, 
        borderRadius: 2,
        transition: 'all 0.2s',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: theme.palette.mode === 'light'
            ? '0 4px 12px rgba(0, 0, 0, 0.1)'
            : '0 4px 12px rgba(0, 0, 0, 0.3)',
        },
      }}
    >
      <Stack direction="row" spacing={2} alignItems="center">
        <Box
          sx={{
            width: 48,
            height: 48,
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: color || 'primary.main',
            color: 'white',
          }}
        >
          {icon}
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
            {label}
          </Typography>
          <Typography variant="h6" fontWeight={700} color={color || 'primary.main'}>
            {value}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, mb: 3 }}>
        Analysis Summary
      </Typography>

      <Grid container spacing={3}>
        {/* Key Metrics */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                Key SEO Metrics
              </Typography>
              <Stack spacing={2}>
                <MetricItem
                  icon={<DomainIcon />}
                  label="Domain Authority (DataForSEO)"
                  value={formatNumber(metrics?.domain_rating_dr)}
                  color="primary.main"
                />
                <MetricItem
                  icon={<TrendingUpIcon />}
                  label="Organic Traffic"
                  value={formatNumber(metrics?.organic_traffic_est)}
                  color="success.main"
                />
                {/* Only show these if not in Backlinks Page Summary to avoid duplication */}
                {!pageStatistics && (
                  <>
                    <MetricItem
                      icon={<LinkIcon />}
                      label="Referring Domains"
                      value={formatNumber(metrics?.total_referring_domains)}
                      color="info.main"
                    />
                    <MetricItem
                      icon={<SearchIcon />}
                      label="Total Backlinks"
                      value={formatNumber(metrics?.total_backlinks)}
                      color="secondary.main"
                    />
                  </>
                )}
                <MetricItem
                  icon={<SearchIcon />}
                  label="Total Keywords"
                  value={formatNumber(metrics?.total_keywords)}
                  color="primary.main"
                />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Keyword Trends */}
        {metrics?.organic_metrics && (
          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                  Keyword Trends
                </Typography>
                <Stack spacing={2}>
                  <MetricItem
                    icon={<TrendingUpIcon />}
                    label="Keywords Moved Up"
                    value={formatNumber(metrics.organic_metrics.is_up)}
                    color="success.main"
                  />
                  <MetricItem
                    icon={<TrendingDownIcon />}
                    label="Keywords Moved Down"
                    value={formatNumber(metrics.organic_metrics.is_down)}
                    color="warning.main"
                  />
                  <MetricItem
                    icon={<NewReleasesIcon />}
                    label="New Keywords"
                    value={formatNumber(metrics.organic_metrics.is_new)}
                    color="info.main"
                  />
                  <MetricItem
                    icon={<RemoveIcon />}
                    label="Lost Keywords"
                    value={formatNumber(metrics.organic_metrics.is_lost)}
                    color="error.main"
                  />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Historical Data */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                Historical Data
              </Typography>
              <Stack spacing={2}>
                <MetricItem
                  icon={<ScheduleIcon />}
                  label="Total Captures"
                  value={formatNumber(wayback?.total_captures)}
                  color="primary.main"
                />
                <MetricItem
                  icon={<ScheduleIcon />}
                  label="First Capture Year"
                  value={wayback?.first_capture_year || 'N/A'}
                  color="primary.main"
                />
                {wayback?.historical_risk_assessment && (
                  <Alert severity="info" sx={{ mt: 2, borderRadius: 2 }}>
                    <Typography variant="body2" fontWeight={600} gutterBottom>
                      Risk Assessment
                    </Typography>
                    <Typography variant="body2">
                      {wayback.historical_risk_assessment}
                    </Typography>
                  </Alert>
                )}
                <Button
                  variant="outlined"
                  size="medium"
                  startIcon={<OpenInNewIcon />}
                  onClick={() => window.open(`https://web.archive.org/web/*/${report.domain_name}`, '_blank')}
                  fullWidth
                  sx={{ mt: 1, borderRadius: 2 }}
                >
                  View on Wayback Machine
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Backlinks Page Summary */}
        {pageStatistics && (
          <Grid item xs={12}>
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                  <AnalyticsIcon sx={{ color: 'primary.main' }} />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Backlinks Page Summary
                  </Typography>
                </Box>

                {/* Summary Cards - Similar to DataForSEOPopup layout */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper
                      sx={{
                        p: 3,
                        bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                        borderRadius: 2,
                        borderLeft: '4px solid #3b82f6',
                        height: '100%',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <LinkIcon sx={{ color: '#3b82f6', fontSize: 24 }} />
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                          Total Backlinks
                        </Typography>
                      </Box>
                      <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'monospace', color: theme.palette.text.primary }}>
                        {formatNumber(pageStatistics.backlinks ?? (pageStatistics as any).backlinks ?? 0)}
                      </Typography>
                    </Paper>
                  </Grid>

                  <Grid item xs={12} sm={6} md={3}>
                    <Paper
                      sx={{
                        p: 3,
                        bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                        borderRadius: 2,
                        borderLeft: '4px solid #10b981',
                        height: '100%',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <DomainIcon sx={{ color: '#10b981', fontSize: 24 }} />
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                          Referring Domains
                        </Typography>
                      </Box>
                      <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'monospace', color: theme.palette.text.primary }}>
                        {formatNumber(pageStatistics.referring_domains ?? (pageStatistics as any).referring_domains ?? 0)}
                      </Typography>
                    </Paper>
                  </Grid>

                  {(pageStatistics as any).referring_pages !== undefined && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 3,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #f59e0b',
                          height: '100%',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <LanguageIcon sx={{ color: '#f59e0b', fontSize: 24 }} />
                          <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                            Referring Pages
                          </Typography>
                        </Box>
                        <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'monospace', color: '#FFFFFF' }}>
                          {formatNumber((pageStatistics as any).referring_pages)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {((pageStatistics as any).backlinks_spam_score !== null && (pageStatistics as any).backlinks_spam_score !== undefined) && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 3,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #ef4444',
                          height: '100%',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <WarningIcon sx={{ color: '#ef4444', fontSize: 24 }} />
                          <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                            Spam Score
                          </Typography>
                        </Box>
                        <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'monospace', color: '#FFFFFF' }}>
                          {`${(pageStatistics as any).backlinks_spam_score}%`}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {/* Domain Rating if available */}
                  {metrics?.domain_rating_dr !== undefined && metrics?.domain_rating_dr !== null && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 3,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #8b5cf6',
                          height: '100%',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <TrendingUpIcon sx={{ color: '#8b5cf6', fontSize: 24 }} />
                          <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                            Domain Rating
                          </Typography>
                        </Box>
                        <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'monospace', color: '#FFFFFF' }}>
                          {metrics.domain_rating_dr}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}
                </Grid>

                {/* Charts - Only show if data is available */}
                {(chartData.tldData.length > 0 || chartData.countryData.length > 0) && (
                  <Grid container spacing={3} sx={{ mt: 2 }}>
                    {chartData.tldData.length > 0 && (
                      <Grid item xs={12} md={6}>
                        <Paper
                          sx={{
                            p: 3,
                            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                            borderRadius: 2,
                            height: '100%',
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                            <LanguageIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                              TLD Distribution
                            </Typography>
                          </Box>
                          <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                              <Pie
                                data={chartData.tldData}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                                outerRadius={100}
                                fill="#8884d8"
                                dataKey="value"
                              >
                                {chartData.tldData.map((entry, index) => (
                                  <Cell
                                    key={`cell-${index}`}
                                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                                  />
                                ))}
                              </Pie>
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: theme.palette.mode === 'dark' ? '#1a1a2e' : '#ffffff',
                                  border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(102, 204, 255, 0.3)' : 'rgba(0, 0, 0, 0.1)'}`,
                                  borderRadius: '8px',
                                  color: theme.palette.text.primary,
                                }}
                              />
                            </PieChart>
                          </ResponsiveContainer>
                        </Paper>
                      </Grid>
                    )}

                    {chartData.countryData.length > 0 && (
                      <Grid item xs={12} md={6}>
                        <Paper
                          sx={{
                            p: 3,
                            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                            borderRadius: 2,
                            height: '100%',
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                            <PublicIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                              Country Breakdown
                            </Typography>
                          </Box>
                          <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={chartData.countryData}>
                              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'} />
                              <XAxis
                                dataKey="name"
                                stroke={theme.palette.text.secondary}
                                style={{ fontSize: '12px' }}
                              />
                              <YAxis stroke={theme.palette.text.secondary} style={{ fontSize: '12px' }} />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: theme.palette.mode === 'dark' ? '#1a1a2e' : '#ffffff',
                                  border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(102, 204, 255, 0.3)' : 'rgba(0, 0, 0, 0.1)'}`,
                                  borderRadius: '8px',
                                  color: theme.palette.text.primary,
                                }}
                              />
                              <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </Paper>
                      </Grid>
                    )}
                  </Grid>
                )}

                {/* Additional Metrics Section */}
                <Grid container spacing={2} sx={{ mt: 3 }}>
                  {/* Referring Domains Details */}
                  {(pageStatistics as any).referring_domains_nofollow !== undefined && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 2,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #06b6d4',
                        }}
                      >
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                          NoFollow Domains
                        </Typography>
                        <Typography variant="h6" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                          {formatNumber((pageStatistics as any).referring_domains_nofollow)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {(pageStatistics as any).referring_main_domains !== undefined && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 2,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #8b5cf6',
                        }}
                      >
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                          Main Domains
                        </Typography>
                        <Typography variant="h6" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                          {formatNumber((pageStatistics as any).referring_main_domains)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {(pageStatistics as any).referring_ips !== undefined && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 2,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #ec4899',
                        }}
                      >
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                          Referring IPs
                        </Typography>
                        <Typography variant="h6" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                          {formatNumber((pageStatistics as any).referring_ips)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {(pageStatistics as any).referring_subnets !== undefined && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 2,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #f97316',
                        }}
                      >
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                          Referring Subnets
                        </Typography>
                        <Typography variant="h6" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                          {formatNumber((pageStatistics as any).referring_subnets)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {(pageStatistics as any).broken_backlinks !== undefined && (pageStatistics as any).broken_backlinks > 0 && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 2,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #ef4444',
                        }}
                      >
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                          Broken Backlinks
                        </Typography>
                        <Typography variant="h6" sx={{ fontWeight: 700, fontFamily: 'monospace', color: 'error.main' }}>
                          {formatNumber((pageStatistics as any).broken_backlinks)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {(pageStatistics as any).broken_pages !== undefined && (pageStatistics as any).broken_pages > 0 && (
                    <Grid item xs={12} sm={6} md={3}>
                      <Paper
                        sx={{
                          p: 2,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                          borderRadius: 2,
                          borderLeft: '4px solid #ef4444',
                        }}
                      >
                        <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                          Broken Pages
                        </Typography>
                        <Typography variant="h6" sx={{ fontWeight: 700, fontFamily: 'monospace', color: 'error.main' }}>
                          {formatNumber((pageStatistics as any).broken_pages)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}
                </Grid>

                {/* Link Types and Attributes */}
                {((pageStatistics as any).referring_links_types || (pageStatistics as any).referring_links_attributes || (pageStatistics as any).referring_links_platform_types) && (
                  <Grid container spacing={2} sx={{ mt: 2 }}>
                    {(pageStatistics as any).referring_links_types && (
                      <Grid item xs={12} md={4}>
                        <Paper
                          sx={{
                            p: 2,
                            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                            borderRadius: 2,
                          }}
                        >
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Link Types
                          </Typography>
                          {Object.entries((pageStatistics as any).referring_links_types).map(([type, count]: [string, any]) => (
                            <Box key={type} sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                              <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                                {type}:
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {formatNumber(count)}
                              </Typography>
                            </Box>
                          ))}
                        </Paper>
                      </Grid>
                    )}

                    {(pageStatistics as any).referring_links_attributes && (
                      <Grid item xs={12} md={4}>
                        <Paper
                          sx={{
                            p: 2,
                            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                            borderRadius: 2,
                          }}
                        >
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Link Attributes
                          </Typography>
                          {Object.entries((pageStatistics as any).referring_links_attributes).map(([attr, count]: [string, any]) => (
                            <Box key={attr} sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                              <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                                {attr}:
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {formatNumber(count)}
                              </Typography>
                            </Box>
                          ))}
                        </Paper>
                      </Grid>
                    )}

                    {(pageStatistics as any).referring_links_platform_types && (
                      <Grid item xs={12} md={4}>
                        <Paper
                          sx={{
                            p: 2,
                            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                            borderRadius: 2,
                          }}
                        >
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Platform Types
                          </Typography>
                          {Object.entries((pageStatistics as any).referring_links_platform_types).map(([platform, count]: [string, any]) => (
                            <Box key={platform} sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                              <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                                {platform}:
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {formatNumber(count)}
                              </Typography>
                            </Box>
                          ))}
                        </Paper>
                      </Grid>
                    )}
                  </Grid>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Loading indicator for page statistics */}
        {loadingPageStats && (
          <Grid item xs={12}>
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, justifyContent: 'center', py: 2 }}>
                  <CircularProgress size={24} />
                  <Typography variant="body2" color="text.secondary">
                    Loading backlinks page summary...
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* AI Analysis Highlights */}
        {llmAnalysis && (
          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                  AI Analysis Highlights
                </Typography>
                <Grid container spacing={2}>
                  {/* Good Highlights */}
                  {llmAnalysis.good_highlights && llmAnalysis.good_highlights.length > 0 && (
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" color="success.main" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
                        <TrendingUpIcon sx={{ fontSize: 18, mr: 0.5, verticalAlign: 'middle' }} />
                        Strengths
                      </Typography>
                      <Stack spacing={1}>
                        {llmAnalysis.good_highlights.map((highlight, index) => (
                          <Chip
                            key={index}
                            label={highlight}
                            color="success"
                            variant="outlined"
                            size="small"
                            sx={{ 
                              justifyContent: 'flex-start', 
                              textAlign: 'left',
                              borderRadius: 1,
                              height: 'auto',
                              py: 0.5,
                              '& .MuiChip-label': {
                                whiteSpace: 'normal',
                                wordBreak: 'break-word',
                              },
                            }}
                          />
                        ))}
                      </Stack>
                    </Grid>
                  )}

                  {/* Bad Highlights */}
                  {llmAnalysis.bad_highlights && llmAnalysis.bad_highlights.length > 0 && (
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" color="error.main" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
                        <TrendingDownIcon sx={{ fontSize: 18, mr: 0.5, verticalAlign: 'middle' }} />
                        Areas for Improvement
                      </Typography>
                      <Stack spacing={1}>
                        {llmAnalysis.bad_highlights.map((highlight, index) => (
                          <Chip
                            key={index}
                            label={highlight}
                            color="error"
                            variant="outlined"
                            size="small"
                            sx={{ 
                              justifyContent: 'flex-start', 
                              textAlign: 'left',
                              borderRadius: 1,
                              height: 'auto',
                              py: 0.5,
                              '& .MuiChip-label': {
                                whiteSpace: 'normal',
                                wordBreak: 'break-word',
                              },
                            }}
                          />
                        ))}
                      </Stack>
                    </Grid>
                  )}
                </Grid>

                {/* Suggested Niches */}
                {llmAnalysis.suggested_niches && llmAnalysis.suggested_niches.length > 0 && (
                  <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
                      Suggested Content Niches
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {llmAnalysis.suggested_niches.map((niche, index) => (
                        <Chip
                          key={index}
                          label={niche}
                          color="primary"
                          variant="filled"
                          size="small"
                          sx={{ borderRadius: 1 }}
                        />
                      ))}
                    </Box>
                  </Box>
                )}

                {/* Confidence Score */}
                {llmAnalysis.confidence_score && (
                  <Box sx={{ mt: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        Analysis Confidence
                      </Typography>
                      <Typography variant="body2" fontWeight={600} color="primary.main">
                        {formatPercentage(llmAnalysis.confidence_score)}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={llmAnalysis.confidence_score * 100}
                      sx={{ 
                        height: 8, 
                        borderRadius: 4,
                        bgcolor: theme.palette.mode === 'light' ? 'rgba(0, 0, 0, 0.08)' : 'rgba(255, 255, 255, 0.12)',
                      }}
                    />
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default ReportSummary;
