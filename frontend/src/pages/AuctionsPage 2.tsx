import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Button,
  Typography,
  CircularProgress,
  LinearProgress,
  Alert,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Paper,
  Container,
  Stack,
  Tabs,
  Tab,
  Chip,
  useTheme,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Refresh as RefreshIcon,
  Assessment as AssessmentIcon,
  TableChart as TableChartIcon,
  FilterList as FilterListIcon,
  Analytics as AnalyticsIcon,
  InsertDriveFile as InsertDriveFileIcon,
} from '@mui/icons-material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApi, AuctionUploadProgress } from '../services/api';
import AuctionsTable from '../components/AuctionsTable';
import Header from '../components/Header';

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

const AuctionsPage: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [auctionSite, setAuctionSite] = useState<string>('namecheap');
  const [sortBy, setSortBy] = useState<string>('expiration_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filters, setFilters] = useState<{
    preferred?: boolean;
    auctionSite?: string;
    offeringType?: string;
    tld?: string;
    tlds?: string[];
    hasStatistics?: boolean;
    scored?: boolean;
    minRank?: number;
    maxRank?: number;
    minScore?: number;
    maxScore?: number;
    expirationFromDate?: string;
    expirationToDate?: string;
  }>({});
  const [page, setPage] = useState<number>(0);
  const [pageSize] = useState<number>(50);
  const [uploadJobId, setUploadJobId] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<AuctionUploadProgress | null>(null);
  const progressPollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [scoringStats, setScoringStats] = useState<{
    unprocessed_count: number;
    processed_count: number;
    scored_count: number;
    total_count: number;
  } | null>(null);
  const [isScoring, setIsScoring] = useState(false);
  const [scoringProgress, setScoringProgress] = useState<{
    batches_processed: number;
    total_processed: number;
    current_batch: number;
  } | null>(null);
  const [scoringStatsError, setScoringStatsError] = useState<string | null>(null);

  const api = useApi();
  const queryClient = useQueryClient();

  // Fetch unique TLDs from database
  const {
    data: tldsData,
    isLoading: isLoadingTlds,
  } = useQuery({
    queryKey: ['auctions-tlds'],
    queryFn: () => api.getUniqueTlds(),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch auctions report
  const {
    data: auctionsData,
    isLoading: isLoadingAuctions,
    error: auctionsError,
    refetch: refetchAuctions,
  } = useQuery({
    queryKey: ['auctions-report', filters, sortBy, sortOrder, searchTerm, page, pageSize],
    queryFn: () =>
      api.getAuctionsReport(
        filters.preferred,
        filters.auctionSite,
        filters.offeringType,
        filters.tld,
        filters.tlds,
        filters.hasStatistics,
        filters.scored,
        filters.minRank,
        filters.maxRank,
        filters.minScore,
        filters.maxScore,
        filters.expirationFromDate,
        filters.expirationToDate,
        undefined, // auctionSites
        sortBy,
        sortOrder,
        pageSize,
        page * pageSize
      ),
    refetchInterval: 30000,
  });

  // CSV upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadAuctionsCSV(file, auctionSite),
    onSuccess: (data) => {
      if (data.job_id) {
        setUploadJobId(data.job_id);
        setUploadProgress(null);
      } else {
        setSelectedFile(null);
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      }
    },
  });

  // Poll for upload progress
  useEffect(() => {
    if (!uploadJobId) {
      if (progressPollIntervalRef.current) {
        clearInterval(progressPollIntervalRef.current);
        progressPollIntervalRef.current = null;
      }
      return;
    }

    const pollProgress = async () => {
      try {
        const progress = await api.getUploadProgress(uploadJobId);
        setUploadProgress(progress);

        if (progress.status === 'completed' || progress.status === 'failed') {
          if (progressPollIntervalRef.current) {
            clearInterval(progressPollIntervalRef.current);
            progressPollIntervalRef.current = null;
          }

          if (progress.status === 'completed') {
            setSelectedFile(null);
            setUploadJobId(null);
            queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
            fetchScoringStats();
          }
        }
      } catch (error) {
        console.error('Failed to fetch upload progress:', error);
      }
    };

    pollProgress();
    progressPollIntervalRef.current = setInterval(pollProgress, 2000);

    return () => {
      if (progressPollIntervalRef.current) {
        clearInterval(progressPollIntervalRef.current);
        progressPollIntervalRef.current = null;
      }
    };
  }, [uploadJobId, api, queryClient]);

  // Fetch scoring statistics
  const fetchScoringStats = async () => {
    try {
      const stats = await api.getScoringStats();
      setScoringStats(stats);
      setScoringStatsError(null);
    } catch (error: any) {
      // Only show error if it's not a 500 (server error) - those are expected if endpoint doesn't exist
      const status = error?.response?.status;
      if (status && status !== 500) {
        setScoringStatsError('Unable to load scoring statistics. Please try again later.');
      } else {
        // For 500 errors, silently fail - endpoint may not be available
        setScoringStatsError(null);
      }
      // Don't set stats to null on error - keep previous stats if available
    }
  };

  useEffect(() => {
    fetchScoringStats();
    const interval = setInterval(fetchScoringStats, 30000);
    return () => clearInterval(interval);
  }, []);

  // Trigger analysis mutation
  const triggerMutation = useMutation({
    mutationFn: (limit: number) => api.triggerAuctionsAnalysis(limit),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
    },
  });

  // Process scoring mutation
  const processScoringMutation = useMutation({
    mutationFn: async (options: { batchSize?: number; continuous?: boolean }) => {
      const { batchSize = 10000, continuous = true } = options;
      setIsScoring(true);
      setScoringProgress({ batches_processed: 0, total_processed: 0, current_batch: 0 });

      let batchNum = 0;
      let totalProcessed = 0;

      try {
        while (true) {
          let stats;
          try {
            stats = await api.getScoringStats();
          } catch (error) {
            throw new Error('Unable to fetch scoring statistics. Please check your connection and try again.');
          }
          if (stats.unprocessed_count === 0) {
            break;
          }

          if (!continuous && batchNum > 0) {
            break;
          }

          batchNum++;
          setScoringProgress(prev => prev ? { ...prev, current_batch: batchNum } : null);

          const result = await api.processScoringBatch(batchSize, undefined, false);

          if (result.success) {
            totalProcessed += result.processed_count;
            setScoringProgress(prev => prev ? {
              ...prev,
              batches_processed: batchNum,
              total_processed: totalProcessed
            } : null);

            try {
              await fetchScoringStats();
            } catch (error) {
              // Silently handle - stats fetch is non-critical during processing
            }
          } else {
            throw new Error(result.error || 'Scoring batch failed');
          }
        }

        try {
          await api.recalculateRankings();
        } catch (error) {
          console.warn('Ranking recalculation failed (non-critical):', error);
        }

        try {
          await fetchScoringStats();
        } catch (error) {
          // Silently handle - stats fetch is non-critical
        }
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });

        return { success: true, batches_processed: batchNum, total_processed: totalProcessed };
      } finally {
        setIsScoring(false);
        setScoringProgress(null);
      }
    },
  });

  // Recalculate rankings mutation
  const recalculateRankingsMutation = useMutation({
    mutationFn: () => api.recalculateRankings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      fetchScoringStats();
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
  };

  const handleTrigger = () => {
    triggerMutation.mutate(100);
  };

  const handleProcessScoring = () => {
    processScoringMutation.mutate({ batchSize: 10000, continuous: true });
  };

  const handleRecalculateRankings = () => {
    recalculateRankingsMutation.mutate();
  };

  const handleSort = (field: string, order: 'asc' | 'desc') => {
    setSortBy(field);
    setSortOrder(order);
    setPage(0);
  };

  const handleSearch = (term: string) => {
    setSearchTerm(term);
    setPage(0);
  };

  const handleFilterChange = (newFilters: {
    preferred?: boolean;
    auctionSite?: string;
    tld?: string;
    hasStatistics?: boolean;
    scored?: boolean;
    minRank?: number;
    maxRank?: number;
    minScore?: number;
    maxScore?: number;
  }) => {
    const cleanedFilters: typeof newFilters = {};

    if (newFilters.preferred !== undefined) cleanedFilters.preferred = newFilters.preferred;
    if (newFilters.auctionSite !== undefined && newFilters.auctionSite !== '') cleanedFilters.auctionSite = newFilters.auctionSite;
    if (newFilters.tld !== undefined && newFilters.tld !== '') cleanedFilters.tld = newFilters.tld;
    if (newFilters.hasStatistics !== undefined) cleanedFilters.hasStatistics = newFilters.hasStatistics;
    if (newFilters.scored !== undefined) cleanedFilters.scored = newFilters.scored;
    if (newFilters.minRank !== undefined && newFilters.minRank !== null && !isNaN(newFilters.minRank)) cleanedFilters.minRank = newFilters.minRank;
    if (newFilters.maxRank !== undefined && newFilters.maxRank !== null && !isNaN(newFilters.maxRank)) cleanedFilters.maxRank = newFilters.maxRank;
    if (newFilters.minScore !== undefined && newFilters.minScore !== null && !isNaN(newFilters.minScore)) cleanedFilters.minScore = newFilters.minScore;
    if (newFilters.maxScore !== undefined && newFilters.maxScore !== null && !isNaN(newFilters.maxScore)) cleanedFilters.maxScore = newFilters.maxScore;

    setFilters(cleanedFilters);
    setPage(0);
  };

  const handleRefresh = () => {
    refetchAuctions();
    fetchScoringStats();
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />
      <Container maxWidth="xl" sx={{ py: { xs: 3, sm: 4 } }}>
        {/* Page Header */}
        <Box sx={{ mb: 4 }}>
          <Typography
            variant="h4"
            component="h1"
            gutterBottom
            sx={{ fontWeight: 700 }}
          >
            Domain Auctions
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Upload, process, and analyze domain auctions from multiple sources
          </Typography>
        </Box>

        {/* Tabs */}
        <Card sx={{ mb: 3 }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            sx={{
              borderBottom: 1,
              borderColor: 'divider',
              px: 2,
            }}
          >
            <Tab
              icon={<InsertDriveFileIcon />}
              iconPosition="start"
              label="Load File"
            />
            <Tab
              icon={<FilterListIcon />}
              iconPosition="start"
              label="Filter & Search"
            />
            <Tab
              icon={<AnalyticsIcon />}
              iconPosition="start"
              label="Data For SEO"
            />
            <Tab
              icon={<TableChartIcon />}
              iconPosition="start"
              label="Table View"
            />
          </Tabs>

          {/* Load File Tab */}
          <TabPanel value={tabValue} index={0}>
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CloudUploadIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Upload CSV File
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Upload a CSV file from any auction site. The table will be truncated before loading new data.
                </Typography>

                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth>
                      <InputLabel>Auction Site</InputLabel>
                      <Select
                        value={auctionSite}
                        onChange={(e) => setAuctionSite(e.target.value)}
                        label="Auction Site"
                      >
                        <MenuItem value="namecheap">Namecheap</MenuItem>
                        <MenuItem value="godaddy">GoDaddy</MenuItem>
                        <MenuItem value="namesilo">NameSilo</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Button
                        variant="outlined"
                        component="label"
                        startIcon={<InsertDriveFileIcon />}
                        disabled={uploadMutation.isPending}
                        fullWidth
                      >
                        {selectedFile ? selectedFile.name : 'Select CSV File'}
                        <input
                          type="file"
                          hidden
                          accept=".csv"
                          onChange={handleFileSelect}
                        />
                      </Button>
                      <Button
                        variant="contained"
                        onClick={handleUpload}
                        disabled={!selectedFile || uploadMutation.isPending}
                        startIcon={uploadMutation.isPending ? <CircularProgress size={20} /> : <CloudUploadIcon />}
                      >
                        {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
                      </Button>
                    </Stack>
                  </Grid>
                </Grid>

                {(uploadMutation.isPending || uploadJobId) && (
                  <Box sx={{ mt: 3 }}>
                    {uploadProgress ? (
                      <>
                        <Box sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                              {uploadProgress.current_stage || 'Processing...'}
                            </Typography>
                            <Typography variant="body2" fontWeight={600}>
                              {uploadProgress.progress_percentage.toFixed(1)}%
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={uploadProgress.progress_percentage}
                            sx={{ height: 8, borderRadius: 4 }}
                          />
                        </Box>
                        <Grid container spacing={2}>
                          <Grid item xs={6} sm={3}>
                            <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center', borderRadius: 2 }}>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                Total Records
                              </Typography>
                              <Typography variant="h6" fontWeight={600}>
                                {uploadProgress.total_records.toLocaleString()}
                              </Typography>
                            </Paper>
                          </Grid>
                          <Grid item xs={6} sm={3}>
                            <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center', borderRadius: 2 }}>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                Processed
                              </Typography>
                              <Typography variant="h6" fontWeight={600}>
                                {uploadProgress.processed_records.toLocaleString()}
                              </Typography>
                            </Paper>
                          </Grid>
                          <Grid item xs={6} sm={3}>
                            <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center', borderRadius: 2 }}>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                Inserted
                              </Typography>
                              <Typography variant="h6" fontWeight={600} color="success.main">
                                {uploadProgress.inserted_count.toLocaleString()}
                              </Typography>
                            </Paper>
                          </Grid>
                          <Grid item xs={6} sm={3}>
                            <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center', borderRadius: 2 }}>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                Skipped
                              </Typography>
                              <Typography variant="h6" fontWeight={600} color="warning.main">
                                {uploadProgress.skipped_count.toLocaleString()}
                              </Typography>
                            </Paper>
                          </Grid>
                        </Grid>
                      </>
                    ) : (
                      <Box>
                        <LinearProgress sx={{ borderRadius: 1, height: 6 }} />
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
                          Starting upload... Please wait.
                        </Typography>
                      </Box>
                    )}
                  </Box>
                )}

                {uploadProgress?.status === 'completed' && (
                  <Alert severity="success" sx={{ mt: 2, borderRadius: 2 }}>
                    <Typography variant="body1" fontWeight={600}>
                      Upload completed successfully!
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                      Processed: {uploadProgress.processed_records.toLocaleString()} records |
                      Inserted: {uploadProgress.inserted_count.toLocaleString()} |
                      Skipped: {uploadProgress.skipped_count.toLocaleString()}
                    </Typography>
                  </Alert>
                )}

                {uploadProgress?.status === 'failed' && (
                  <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }}>
                    <Typography variant="body1" fontWeight={600}>
                      Upload failed
                    </Typography>
                    {uploadProgress.error_message && (
                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                        {uploadProgress.error_message}
                      </Typography>
                    )}
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Scoring Section */}
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AssessmentIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Score & Rank Auctions
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Process and score all unprocessed auction records. This will calculate scores and rankings for all domains.
                </Typography>

                {scoringStatsError && (
                  <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
                    <Typography variant="body2">
                      Scoring statistics are currently unavailable. The scoring feature may require backend configuration.
                    </Typography>
                  </Alert>
                )}

                {!scoringStats && !scoringStatsError && (
                  <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
                    <Typography variant="body2">
                      Loading scoring statistics...
                    </Typography>
                  </Alert>
                )}

                {scoringStats && (
                  <Paper variant="outlined" sx={{ mb: 3, p: 3, borderRadius: 2 }}>
                    <Grid container spacing={3}>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                          Total Records
                        </Typography>
                        <Typography variant="h6" fontWeight={600}>
                          {scoringStats.total_count.toLocaleString()}
                        </Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                          Processed
                        </Typography>
                        <Typography variant="h6" fontWeight={600} color="success.main">
                          {scoringStats.processed_count.toLocaleString()}
                        </Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                          Unprocessed
                        </Typography>
                        <Typography variant="h6" fontWeight={600} color={scoringStats.unprocessed_count > 0 ? "warning.main" : "success.main"}>
                          {scoringStats.unprocessed_count.toLocaleString()}
                        </Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                          Scored
                        </Typography>
                        <Typography variant="h6" fontWeight={600} color="info.main">
                          {scoringStats.scored_count.toLocaleString()}
                        </Typography>
                      </Grid>
                    </Grid>
                    {scoringStats.total_count > 0 && (
                      <Box sx={{ mt: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            Progress
                          </Typography>
                          <Typography variant="body2" fontWeight={600}>
                            {((scoringStats.processed_count / scoringStats.total_count) * 100).toFixed(1)}%
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={(scoringStats.processed_count / scoringStats.total_count) * 100}
                          sx={{ height: 8, borderRadius: 4 }}
                        />
                      </Box>
                    )}
                  </Paper>
                )}

                {scoringProgress && (
                  <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
                    <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                      Processing Scoring...
                    </Typography>
                    <Typography variant="body2">
                      Batch {scoringProgress.current_batch} |
                      Processed: {scoringProgress.total_processed.toLocaleString()} records
                    </Typography>
                  </Alert>
                )}

                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    onClick={handleProcessScoring}
                    disabled={isScoring || !scoringStats || (scoringStats?.unprocessed_count ?? 0) === 0 || !!scoringStatsError}
                    startIcon={isScoring ? <CircularProgress size={20} color="inherit" /> : <AssessmentIcon />}
                  >
                    {isScoring ? 'Processing...' : 'Process Scoring'}
                  </Button>

                  <Button
                    variant="outlined"
                    color="secondary"
                    size="large"
                    onClick={handleRecalculateRankings}
                    disabled={recalculateRankingsMutation.isPending || !scoringStats || (scoringStats?.scored_count ?? 0) === 0 || !!scoringStatsError}
                    startIcon={recalculateRankingsMutation.isPending ? <CircularProgress size={20} /> : <RefreshIcon />}
                  >
                    {recalculateRankingsMutation.isPending ? 'Recalculating...' : 'Recalculate Rankings'}
                  </Button>

                  <Button
                    variant="outlined"
                    size="large"
                    onClick={fetchScoringStats}
                    startIcon={<RefreshIcon />}
                  >
                    Refresh Stats
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Filter & Search Tab */}
          <TabPanel value={tabValue} index={1}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                  Filters & Search
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Use the table below to filter and search auctions. Filters are applied in real-time.
                </Typography>
                {auctionsData && (
                  <AuctionsTable
                    auctions={auctionsData.auctions}
                    onSort={handleSort}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                    onSearch={handleSearch}
                    onFilterChange={handleFilterChange}
                    totalCount={auctionsData.total_count}
                    hasMore={auctionsData.has_more}
                    page={page}
                    onPageChange={setPage}
                    pageSize={pageSize}
                    availableTlds={tldsData || []}
                  />
                )}
              </CardContent>
            </Card>
          </TabPanel>

          {/* Data For SEO Tab */}
          <TabPanel value={tabValue} index={2}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AnalyticsIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    DataForSEO Analysis
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Select up to 100 most recent scored domains without page_statistics and trigger DataForSEO bulk page summary analysis.
                  Note: DataForSEO API allows up to 100 unique domains per request. Results will be stored in the page_statistics field.
                </Typography>

                <Button
                  variant="contained"
                  color="secondary"
                  size="large"
                  onClick={handleTrigger}
                  disabled={triggerMutation.isPending}
                  startIcon={triggerMutation.isPending ? <CircularProgress size={20} /> : <AssessmentIcon />}
                >
                  {triggerMutation.isPending ? 'Triggering Analysis...' : 'Trigger DataForSEO Analysis'}
                </Button>

                {triggerMutation.isSuccess && (
                  <Alert severity="success" sx={{ mt: 2, borderRadius: 2 }}>
                    <Typography variant="body1" fontWeight={600}>
                      {triggerMutation.data.message}
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                      Triggered: {triggerMutation.data.triggered_count}, Skipped: {triggerMutation.data.skipped_count}
                    </Typography>
                  </Alert>
                )}

                {triggerMutation.isError && (
                  <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }}>
                    Trigger failed: {triggerMutation.error instanceof Error ? triggerMutation.error.message : 'Unknown error'}
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabPanel>

          {/* Table View Tab */}
          <TabPanel value={tabValue} index={3}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Auctions Report
                  </Typography>
                  <Button
                    variant="outlined"
                    startIcon={<RefreshIcon />}
                    onClick={handleRefresh}
                    disabled={isLoadingAuctions}
                  >
                    Refresh
                  </Button>
                </Box>

                {isLoadingAuctions && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                )}

                {auctionsError && (
                  <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
                    Failed to load auctions: {auctionsError instanceof Error ? auctionsError.message : 'Unknown error'}
                  </Alert>
                )}

                {auctionsData && (
                  <AuctionsTable
                    auctions={auctionsData.auctions}
                    onSort={handleSort}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                    onSearch={handleSearch}
                    onFilterChange={handleFilterChange}
                    totalCount={auctionsData.total_count}
                    hasMore={auctionsData.has_more}
                    page={page}
                    onPageChange={setPage}
                    pageSize={pageSize}
                    availableTlds={tldsData || []}
                  />
                )}
              </CardContent>
            </Card>
          </TabPanel>
        </Card>
      </Container>
    </Box>
  );
};

export default AuctionsPage;
