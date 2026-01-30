import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  CircularProgress,
  Button,
  Tabs,
  Tab,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Container,
  Stack,
  useTheme,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  Delete as DeleteIcon,
  Analytics as AnalyticsIcon,
  History as HistoryIcon,
  Lightbulb as LightbulbIcon,
  TableChart as TableChartIcon,
  Link as LinkIcon,
  Search as SearchIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';

import { useApi, DomainAnalysisReport, ReportResponse } from '../services/api';
import ReportSummary from '../components/ReportSummary';
import KeywordsTable from '../components/KeywordsTable';
import BacklinksTable from '../components/BacklinksTable';
import LLMAnalysis from '../components/LLMAnalysis';
import DomainRankings from '../components/DomainRankings';
import AnalysisProgress from '../components/AnalysisProgress';
import DevelopmentPlan from '../components/DevelopmentPlan';
import Header from '../components/Header';
import HistoricalDataChart from '../components/HistoricalDataChart';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const ReportPage: React.FC = () => {
  const { domain } = useParams<{ domain: string }>();
  const navigate = useNavigate();
  const api = useApi();
  const queryClient = useQueryClient();
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [retryDialogOpen, setRetryDialogOpen] = useState(false);

  // Fetch report data
  const {
    data: reportData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['report', domain],
    queryFn: () => api.getReport(domain!),
    enabled: !!domain,
    refetchInterval: (query) => {
      const data = query.state.data as ReportResponse | undefined;
      const status = data?.report?.status;
      const shouldPoll = status === 'in_progress' || status === undefined;
      return shouldPoll ? 2000 : false;
    },
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  });

  // Retry analysis mutation
  const retryMutation = useMutation({
    mutationFn: () => api.retryAnalysis(domain!),
    onSuccess: () => {
      setRetryDialogOpen(false);
      refetch();
    },
  });

  // Delete report mutation
  const deleteMutation = useMutation({
    mutationFn: () => api.deleteReport(domain!),
    onSuccess: () => {
      navigate('/reports');
    },
  });

  const report = reportData?.report;
  const prevStatusRef = useRef<string | undefined>(undefined);

  // Force refetch when status changes from in_progress to completed
  useEffect(() => {
    const currentStatus = report?.status;
    const prevStatus = prevStatusRef.current;

    if (prevStatus === 'in_progress' && currentStatus === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['report', domain] });
      setTimeout(() => {
        refetch();
      }, 100);
    }

    if (currentStatus === 'completed' && prevStatus !== 'completed') {
      queryClient.invalidateQueries({ queryKey: ['report', domain] });
    }

    prevStatusRef.current = currentStatus;
  }, [report?.status, refetch, queryClient, domain]);

  // Additional safety check
  useEffect(() => {
    if (!domain || isLoading) return;

    const currentStatus = report?.status;

    if (currentStatus !== 'in_progress' && currentStatus !== undefined) {
      return;
    }

    const checkInterval = setInterval(async () => {
      try {
        const freshData = await api.getReport(domain);
        const freshStatus = freshData?.report?.status;

        if (freshStatus === 'completed' && (currentStatus === 'in_progress' || currentStatus === undefined)) {
          queryClient.invalidateQueries({ queryKey: ['report', domain] });
          refetch();
        }
      } catch (err) {
        console.error('Error checking report status:', err);
      }
    }, 3000);

    return () => clearInterval(checkInterval);
  }, [domain, report?.status, isLoading, api, queryClient, refetch]);

  useEffect(() => {
    if (domain && !isLoading) {
      const currentStatus = report?.status;
      if (currentStatus === 'in_progress' || !currentStatus) {
        refetch();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRetry = () => {
    retryMutation.mutate();
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this report?')) {
      deleteMutation.mutate();
    }
  };

  const handleExportPDF = () => {
    const baseUrl = process.env.REACT_APP_API_URL || '/api/v1';
    const pdfUrl = `${baseUrl}/reports/${domain}/pdf`;
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = `domain_analysis_${domain}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'in_progress':
        return <CircularProgress size={20} />;
      default:
        return <ScheduleIcon color="action" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'in_progress':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="lg" sx={{ py: 8 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <CircularProgress />
            <Typography color="text.secondary">Loading report...</Typography>
          </Box>
        </Container>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
            Failed to load report: {error.message}
          </Alert>
          <Button variant="outlined" onClick={() => navigate('/')}>
            Back to Analysis
          </Button>
        </Container>
      </Box>
    );
  }

  if (!report) {
    const isAnalysisInProgress = reportData?.message?.includes('Status: AnalysisStatus.PENDING') ||
      reportData?.message?.includes('Status: AnalysisStatus.IN_PROGRESS');
    const isAnalysisFailed = reportData?.message?.includes('Status: AnalysisStatus.FAILED');

    if (isAnalysisInProgress) {
      return (
        <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
          <Header />
          <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <IconButton onClick={() => navigate('/')} sx={{ mr: 2 }}>
                <ArrowBackIcon />
              </IconButton>
              <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }}>
                Analysis in Progress: {domain}
              </Typography>
            </Box>
            <AnalysisProgress
              domain={domain!}
              onComplete={() => refetch()}
            />
          </Container>
        </Box>
      );
    }

    if (isAnalysisFailed) {
      return (
        <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
          <Header />
          <Container maxWidth="lg" sx={{ py: 4 }}>
            <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
              <Typography variant="h6" gutterBottom>
                Analysis Failed
              </Typography>
              <Typography variant="body2">
                {reportData?.message || 'Analysis failed. Please try again.'}
              </Typography>
            </Alert>
            <Button variant="outlined" onClick={() => navigate('/')}>
              Back to Analysis
            </Button>
          </Container>
        </Box>
      );
    }

    return (
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Alert severity="warning" sx={{ mb: 2, borderRadius: 2 }}>
            Report not found for domain: {domain}
          </Alert>
          <Button variant="outlined" onClick={() => navigate('/')}>
            Back to Analysis
          </Button>
        </Container>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />
      <Container maxWidth="lg" sx={{ py: { xs: 3, sm: 4 } }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <IconButton
              onClick={() => navigate('/reports')}
              sx={{
                mr: 2,
                '&:hover': {
                  backgroundColor: theme.palette.mode === 'light'
                    ? 'rgba(0, 0, 0, 0.04)'
                    : 'rgba(255, 255, 255, 0.08)',
                },
              }}
            >
              <ArrowBackIcon />
            </IconButton>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h4" component="h1" sx={{ fontWeight: 700, mb: 1 }}>
                {report.domain_name}
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'flex-start', sm: 'center' }}>
                <Chip
                  icon={getStatusIcon(report.status)}
                  label={report.status.replace('_', ' ').toUpperCase()}
                  color={getStatusColor(report.status) as any}
                  variant="outlined"
                  sx={{ borderRadius: 1 }}
                />
                {report.analysis_timestamp && (
                  <Typography variant="body2" color="text.secondary">
                    Analyzed: {new Date(report.analysis_timestamp).toLocaleString()}
                  </Typography>
                )}
                {report.processing_time_seconds && (
                  <Typography variant="body2" color="text.secondary">
                    Processing time: {report.processing_time_seconds.toFixed(1)}s
                  </Typography>
                )}
              </Stack>
            </Box>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Tooltip title="Refresh">
                <IconButton
                  onClick={() => refetch()}
                  sx={{
                    '&:hover': {
                      backgroundColor: theme.palette.mode === 'light'
                        ? 'rgba(0, 0, 0, 0.04)'
                        : 'rgba(255, 255, 255, 0.08)',
                    },
                  }}
                >
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportPDF}
                disabled={report.status !== 'completed'}
                size="small"
              >
                Export PDF
              </Button>
              {report.status === 'failed' && (
                <Button
                  variant="outlined"
                  color="warning"
                  onClick={() => setRetryDialogOpen(true)}
                  disabled={retryMutation.isPending}
                  size="small"
                >
                  Retry
                </Button>
              )}
              <Button
                variant="outlined"
                color="error"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                startIcon={<DeleteIcon />}
                size="small"
              >
                Delete
              </Button>
            </Stack>
          </Box>
        </Box>

        {/* Enhanced progress indicator for in-progress analysis */}
        {report.status === 'in_progress' && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <AnalysisProgress
                domain={domain!}
                onComplete={() => refetch()}
              />
            </CardContent>
          </Card>
        )}

        {/* Error message for failed analysis */}
        {report.status === 'failed' && report.error_message && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              Analysis Failed
            </Typography>
            <Typography variant="body2">
              {report.error_message}
            </Typography>
          </Alert>
        )}

        {/* Report content */}
        {report.status === 'completed' && (
          <>
            {/* Summary Card */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <ReportSummary report={report} />
              </CardContent>
            </Card>

            {/* Tabs for detailed views */}
            <Card>
              <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
                <Tabs
                  value={tabValue}
                  onChange={handleTabChange}
                  variant="scrollable"
                  scrollButtons="auto"
                >
                  <Tab
                    icon={<AnalyticsIcon />}
                    iconPosition="start"
                    label="Overview"
                  />
                  <Tab
                    icon={<TrendingUpIcon />}
                    iconPosition="start"
                    label="Domain Rankings"
                  />
                  <Tab
                    icon={<SearchIcon />}
                    iconPosition="start"
                    label="Keywords"
                  />
                  <Tab
                    icon={<LinkIcon />}
                    iconPosition="start"
                    label="Backlinks"
                  />
                  <Tab
                    icon={<LightbulbIcon />}
                    iconPosition="start"
                    label="AI Analysis"
                  />
                  <Tab
                    icon={<HistoryIcon />}
                    iconPosition="start"
                    label="Historical Data"
                  />
                  <Tab
                    icon={<AssessmentIcon />}
                    iconPosition="start"
                    label="Development Plan"
                  />
                </Tabs>
              </Box>

              <TabPanel value={tabValue} index={0}>
                <Grid container spacing={3}>
                  {/* SEO Metrics */}
                  {report.data_for_seo_metrics && (
                    <Grid item xs={12} md={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 2 }}>
                            SEO Metrics
                          </Typography>
                          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                            <Table size="small">
                              <TableBody>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 500 }}>Domain Authority</TableCell>
                                  <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                      {report.data_for_seo_metrics.domain_rating_dr || 'N/A'}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 500 }}>Organic Traffic</TableCell>
                                  <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                      {report.data_for_seo_metrics.organic_traffic_est?.toLocaleString() || 'N/A'}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 500 }}>Referring Domains</TableCell>
                                  <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                      {report.data_for_seo_metrics.total_referring_domains?.toLocaleString() || 'N/A'}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 500 }}>Total Backlinks</TableCell>
                                  <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                      {report.data_for_seo_metrics.total_backlinks?.toLocaleString() || 'N/A'}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}

                  {/* Historical Data */}
                  {report.wayback_machine_summary && (
                    <Grid item xs={12} md={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 2 }}>
                            Historical Data
                          </Typography>
                          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                            <Table size="small">
                              <TableBody>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 500 }}>Total Captures</TableCell>
                                  <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                      {report.wayback_machine_summary.total_captures?.toLocaleString() || 'N/A'}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 500 }}>First Capture Year</TableCell>
                                  <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                      {report.wayback_machine_summary.first_capture_year || 'N/A'}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 500 }}>Last Capture</TableCell>
                                  <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                      {report.wayback_machine_summary.last_capture_date
                                        ? new Date(report.wayback_machine_summary.last_capture_date).toLocaleDateString()
                                        : 'N/A'}
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                                {report.wayback_machine_summary.earliest_snapshot_url && (
                                  <TableRow>
                                    <TableCell sx={{ fontWeight: 500 }}>Earliest Snapshot</TableCell>
                                    <TableCell align="right">
                                      <Button
                                        size="small"
                                        endIcon={<OpenInNewIcon />}
                                        onClick={() => window.open(report.wayback_machine_summary!.earliest_snapshot_url)}
                                        sx={{ borderRadius: 1 }}
                                      >
                                        View
                                      </Button>
                                    </TableCell>
                                  </TableRow>
                                )}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                </Grid>
              </TabPanel>

              <TabPanel value={tabValue} index={1}>
                <DomainRankings metrics={report.data_for_seo_metrics} domain={report.domain_name} />
              </TabPanel>

              <TabPanel value={tabValue} index={2}>
                <KeywordsTable domain={domain!} reportData={report} />
              </TabPanel>

              <TabPanel value={tabValue} index={3}>
                <BacklinksTable domain={domain!} reportData={report} />
              </TabPanel>

              <TabPanel value={tabValue} index={4}>
                <LLMAnalysis analysis={report.llm_analysis} domain={domain!} />
              </TabPanel>

              <TabPanel value={tabValue} index={5}>
                <HistoricalDataChart domain={domain!} data={report.historical_data} />
              </TabPanel>

              <TabPanel value={tabValue} index={6}>
                <DevelopmentPlan domain={domain!} reportData={report} />
              </TabPanel>
            </Card>
          </>
        )}

        {/* Retry Dialog */}
        <Dialog
          open={retryDialogOpen}
          onClose={() => setRetryDialogOpen(false)}
          PaperProps={{
            sx: {
              borderRadius: 2,
            },
          }}
        >
          <DialogTitle sx={{ fontWeight: 600 }}>Retry Analysis</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to retry the analysis for {domain}? This will start a new analysis process.
            </Typography>
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button onClick={() => setRetryDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleRetry}
              variant="contained"
              disabled={retryMutation.isPending}
            >
              {retryMutation.isPending ? <CircularProgress size={20} /> : 'Retry'}
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    </Box>
  );
};

export default ReportPage;
