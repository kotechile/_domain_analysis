import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment,
  Pagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  TableSortLabel,
  Container,
  Stack,
  CircularProgress,
  useTheme,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { useApi, DomainAnalysisReport } from '../services/api';
import { formatDate } from '../utils/dateUtils';
import Header from '../components/Header';

type SortField = 'domain_name' | 'analysis_timestamp' | 'domain_rating_dr' | 'organic_traffic_est' | 'total_backlinks' | 'total_keywords';
type SortDirection = 'asc' | 'desc';

const ReportsListPage: React.FC = () => {
  const navigate = useNavigate();
  const api = useApi();
  const queryClient = useQueryClient();
  const theme = useTheme();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [domainToDelete, setDomainToDelete] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('analysis_timestamp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const limit = 10;
  const offset = (page - 1) * limit;

  // Fetch reports
  const {
    data: reports,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['reports', { limit, offset, searchTerm }],
    queryFn: () => api.listReports(limit, offset),
  });

  // Delete report mutation
  const deleteMutation = useMutation({
    mutationFn: (domain: string) => api.deleteReport(domain),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      setDeleteDialogOpen(false);
      setDomainToDelete(null);
    },
  });

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setPage(1);
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, newPage: number) => {
    setPage(newPage);
  };

  const handleViewReport = (domain: string) => {
    navigate(`/reports/${domain}`);
  };

  const handleDeleteClick = (domain: string) => {
    setDomainToDelete(domain);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (domainToDelete) {
      deleteMutation.mutate(domainToDelete);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" fontSize="small" />;
      case 'failed':
        return <ErrorIcon color="error" fontSize="small" />;
      case 'in_progress':
        return <ScheduleIcon color="warning" fontSize="small" />;
      default:
        return <ScheduleIcon color="action" fontSize="small" />;
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

  const formatNumber = (num: number | undefined | null) => {
    if (num === undefined || num === null) return 'N/A';
    return num.toLocaleString();
  };

  // Filter and sort reports
  const filteredReports = reports?.filter((report) =>
    report.domain_name.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Sort reports
  const sortedReports = [...filteredReports].sort((a, b) => {
    let aValue: any;
    let bValue: any;

    switch (sortField) {
      case 'domain_name':
        aValue = a.domain_name;
        bValue = b.domain_name;
        break;
      case 'analysis_timestamp':
        aValue = new Date(a.analysis_timestamp);
        bValue = new Date(b.analysis_timestamp);
        break;
      case 'domain_rating_dr':
        aValue = a.data_for_seo_metrics?.domain_rating_dr || 0;
        bValue = b.data_for_seo_metrics?.domain_rating_dr || 0;
        break;
      case 'organic_traffic_est':
        aValue = a.data_for_seo_metrics?.organic_traffic_est || 0;
        bValue = b.data_for_seo_metrics?.organic_traffic_est || 0;
        break;
      case 'total_backlinks':
        aValue = a.data_for_seo_metrics?.total_backlinks || 0;
        bValue = b.data_for_seo_metrics?.total_backlinks || 0;
        break;
      case 'total_keywords':
        aValue = a.data_for_seo_metrics?.total_keywords || 0;
        bValue = b.data_for_seo_metrics?.total_keywords || 0;
        break;
      default:
        return 0;
    }

    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  if (isLoading) {
    return (
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="lg" sx={{ py: 8 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <CircularProgress />
            <Typography color="text.secondary">Loading reports...</Typography>
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
            Failed to load reports: {error.message}
          </Alert>
          <Button variant="outlined" onClick={() => refetch()}>
            Retry
          </Button>
        </Container>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />
      <Container maxWidth="lg" sx={{ py: { xs: 3, sm: 4 } }}>
        {/* Page Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 700, mb: 1 }}>
              Domain Analysis Reports
            </Typography>
            <Typography variant="body2" color="text.secondary">
              View and manage your domain analysis reports
            </Typography>
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/')}
            >
              New Analysis
            </Button>
          </Stack>
        </Box>

        {/* Search */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <TextField
              fullWidth
              placeholder="Search reports by domain name..."
              value={searchTerm}
              onChange={handleSearch}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />
          </CardContent>
        </Card>

        {/* Reports Table */}
        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'domain_name'}
                      direction={sortField === 'domain_name' ? sortDirection : 'asc'}
                      onClick={() => handleSort('domain_name')}
                    >
                      Domain
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'analysis_timestamp'}
                      direction={sortField === 'analysis_timestamp' ? sortDirection : 'asc'}
                      onClick={() => handleSort('analysis_timestamp')}
                    >
                      Analysis Date
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>Processing Time</TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'domain_rating_dr'}
                      direction={sortField === 'domain_rating_dr' ? sortDirection : 'asc'}
                      onClick={() => handleSort('domain_rating_dr')}
                    >
                      Domain Authority
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'organic_traffic_est'}
                      direction={sortField === 'organic_traffic_est' ? sortDirection : 'asc'}
                      onClick={() => handleSort('organic_traffic_est')}
                    >
                      Traffic
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'total_backlinks'}
                      direction={sortField === 'total_backlinks' ? sortDirection : 'asc'}
                      onClick={() => handleSort('total_backlinks')}
                    >
                      Backlinks
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'total_keywords'}
                      direction={sortField === 'total_keywords' ? sortDirection : 'asc'}
                      onClick={() => handleSort('total_keywords')}
                    >
                      Keywords
                    </TableSortLabel>
                  </TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedReports.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 6 }}>
                      <AssessmentIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                      <Typography variant="h6" color="text.secondary" gutterBottom>
                        {searchTerm ? 'No reports found matching your search' : 'No reports available'}
                      </Typography>
                      {!searchTerm && (
                        <Button
                          variant="contained"
                          startIcon={<AddIcon />}
                          onClick={() => navigate('/')}
                          sx={{ mt: 2 }}
                        >
                          Start Your First Analysis
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedReports.map((report) => (
                    <TableRow 
                      key={report.domain_name} 
                      hover
                      sx={{
                        '&:hover': {
                          backgroundColor: theme.palette.mode === 'light' 
                            ? 'rgba(0, 0, 0, 0.04)' 
                            : 'rgba(255, 255, 255, 0.08)',
                        },
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {report.domain_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          icon={getStatusIcon(report.status)}
                          label={report.status.replace('_', ' ').toUpperCase()}
                          color={getStatusColor(report.status) as any}
                          size="small"
                          variant="outlined"
                          sx={{ borderRadius: 1 }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatDate(report.analysis_timestamp)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {report.processing_time_seconds
                            ? `${report.processing_time_seconds.toFixed(1)}s`
                            : 'N/A'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {formatNumber(report.data_for_seo_metrics?.domain_rating_dr)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {formatNumber(report.data_for_seo_metrics?.organic_traffic_est)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {formatNumber(report.data_for_seo_metrics?.total_backlinks)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {formatNumber(report.data_for_seo_metrics?.total_keywords)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Tooltip title="View Report">
                            <IconButton
                              size="small"
                              onClick={() => handleViewReport(report.domain_name)}
                              sx={{
                                '&:hover': {
                                  backgroundColor: 'primary.main',
                                  color: 'primary.contrastText',
                                },
                              }}
                            >
                              <VisibilityIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete Report">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteClick(report.domain_name)}
                              disabled={deleteMutation.isPending}
                              sx={{
                                '&:hover': {
                                  backgroundColor: 'error.main',
                                  color: 'error.contrastText',
                                },
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Pagination */}
          {filteredReports.length > 0 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <Pagination
                count={Math.ceil((reports?.length || 0) / limit)}
                page={page}
                onChange={handlePageChange}
                color="primary"
                size="large"
                showFirstButton
                showLastButton
                sx={{
                  '& .MuiPaginationItem-root': {
                    borderRadius: 1,
                  },
                }}
              />
            </Box>
          )}
        </Card>

        {/* Delete Confirmation Dialog */}
        <Dialog 
          open={deleteDialogOpen} 
          onClose={() => setDeleteDialogOpen(false)}
          PaperProps={{
            sx: {
              borderRadius: 2,
            },
          }}
        >
          <DialogTitle sx={{ fontWeight: 600 }}>Delete Report</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to delete the analysis report for{' '}
              <strong>{domainToDelete}</strong>? This action cannot be undone.
            </Typography>
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleDeleteConfirm}
              color="error"
              variant="contained"
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    </Box>
  );
};

export default ReportsListPage;
