import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';

import { useApi, DomainAnalysisReport } from '../services/api';
import ReportSummary from '../components/ReportSummary';
import KeywordsTable from '../components/KeywordsTable';
import BacklinksTable from '../components/BacklinksTable';
import LLMAnalysis from '../components/LLMAnalysis';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`report-tabpanel-${index}`}
      aria-labelledby={`report-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const ReportPage: React.FC = () => {
  const { domain } = useParams<{ domain: string }>();
  const navigate = useNavigate();
  const api = useApi();
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
    refetchInterval: (data) => {
      // Refetch every 2 seconds if analysis is in progress
      return data?.report?.status === 'in_progress' ? 2000 : false;
    },
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
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load report: {error.message}
        </Alert>
        <Button variant="outlined" onClick={() => navigate('/')}>
          Back to Analysis
        </Button>
      </Box>
    );
  }

  if (!report) {
    return (
      <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Report not found for domain: {domain}
        </Alert>
        <Button variant="outlined" onClick={() => navigate('/')}>
          Back to Analysis
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate('/')} sx={{ mr: 2 }}>
          <ArrowBackIcon />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" component="h1">
            {report.domain_name}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
            <Chip
              icon={getStatusIcon(report.status)}
              label={report.status.replace('_', ' ').toUpperCase()}
              color={getStatusColor(report.status) as any}
              variant="outlined"
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
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={() => refetch()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          {report.status === 'failed' && (
            <Button
              variant="outlined"
              color="warning"
              onClick={() => setRetryDialogOpen(true)}
              disabled={retryMutation.isPending}
            >
              Retry Analysis
            </Button>
          )}
          <Button
            variant="outlined"
            color="error"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            Delete
          </Button>
        </Box>
      </Box>

      {/* Progress indicator for in-progress analysis */}
      {report.status === 'in_progress' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <CircularProgress size={24} />
              <Typography variant="h6">Analysis in Progress</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Collecting data from external APIs and generating AI insights...
            </Typography>
            <LinearProgress />
          </CardContent>
        </Card>
      )}

      {/* Error message for failed analysis */}
      {report.status === 'failed' && report.error_message && (
        <Alert severity="error" sx={{ mb: 3 }}>
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
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={handleTabChange}>
                <Tab label="Overview" />
                <Tab label="Keywords" />
                <Tab label="Backlinks" />
                <Tab label="AI Analysis" />
                <Tab label="Historical Data" />
              </Tabs>
            </Box>

            <TabPanel value={tabValue} index={0}>
              <Grid container spacing={3}>
                {/* SEO Metrics */}
                {report.data_for_seo_metrics && (
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" gutterBottom>
                      SEO Metrics
                    </Typography>
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell>Domain Rating (DR)</TableCell>
                            <TableCell align="right">
                              {report.data_for_seo_metrics.domain_rating_dr || 'N/A'}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Organic Traffic</TableCell>
                            <TableCell align="right">
                              {report.data_for_seo_metrics.organic_traffic_est?.toLocaleString() || 'N/A'}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Referring Domains</TableCell>
                            <TableCell align="right">
                              {report.data_for_seo_metrics.total_referring_domains?.toLocaleString() || 'N/A'}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Total Backlinks</TableCell>
                            <TableCell align="right">
                              {report.data_for_seo_metrics.total_backlinks?.toLocaleString() || 'N/A'}
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Grid>
                )}

                {/* Historical Data */}
                {report.wayback_machine_summary && (
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" gutterBottom>
                      Historical Data
                    </Typography>
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell>Total Captures</TableCell>
                            <TableCell align="right">
                              {report.wayback_machine_summary.total_captures?.toLocaleString() || 'N/A'}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>First Capture Year</TableCell>
                            <TableCell align="right">
                              {report.wayback_machine_summary.first_capture_year || 'N/A'}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Last Capture</TableCell>
                            <TableCell align="right">
                              {report.wayback_machine_summary.last_capture_date
                                ? new Date(report.wayback_machine_summary.last_capture_date).toLocaleDateString()
                                : 'N/A'}
                            </TableCell>
                          </TableRow>
                          {report.wayback_machine_summary.earliest_snapshot_url && (
                            <TableRow>
                              <TableCell>Earliest Snapshot</TableCell>
                              <TableCell align="right">
                                <Button
                                  size="small"
                                  endIcon={<OpenInNewIcon />}
                                  onClick={() => window.open(report.wayback_machine_summary!.earliest_snapshot_url)}
                                >
                                  View
                                </Button>
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Grid>
                )}
              </Grid>
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <KeywordsTable domain={domain!} />
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              <BacklinksTable domain={domain!} />
            </TabPanel>

            <TabPanel value={tabValue} index={3}>
              <LLMAnalysis analysis={report.llm_analysis} />
            </TabPanel>

            <TabPanel value={tabValue} index={4}>
              {report.wayback_machine_summary?.historical_risk_assessment ? (
                <Alert severity="info">
                  <Typography variant="h6" gutterBottom>
                    Historical Risk Assessment
                  </Typography>
                  <Typography variant="body2">
                    {report.wayback_machine_summary.historical_risk_assessment}
                  </Typography>
                </Alert>
              ) : (
                <Typography color="text.secondary">
                  No historical data available
                </Typography>
              )}
            </TabPanel>
          </Card>
        </>
      )}

      {/* Retry Dialog */}
      <Dialog open={retryDialogOpen} onClose={() => setRetryDialogOpen(false)}>
        <DialogTitle>Retry Analysis</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to retry the analysis for {domain}? This will start a new analysis process.
          </Typography>
        </DialogContent>
        <DialogActions>
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
    </Box>
  );
};

export default ReportPage;
