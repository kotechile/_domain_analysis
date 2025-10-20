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
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { useApi, DomainAnalysisReport } from '../services/api';

const ReportsListPage: React.FC = () => {
  const navigate = useNavigate();
  const api = useApi();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [domainToDelete, setDomainToDelete] = useState<string | null>(null);

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
    setPage(1); // Reset to first page when searching
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatNumber = (num: number | undefined) => {
    if (num === undefined) return 'N/A';
    return num.toLocaleString();
  };

  // Filter reports based on search term
  const filteredReports = reports?.filter((report) =>
    report.domain_name.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Typography>Loading reports...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load reports: {error.message}
        </Alert>
        <Button variant="outlined" onClick={() => refetch()}>
          Retry
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Domain Analysis Reports
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
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
        </Box>
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
          />
        </CardContent>
      </Card>

      {/* Reports Table */}
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Domain</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Analysis Date</TableCell>
                <TableCell>Processing Time</TableCell>
                <TableCell>DR</TableCell>
                <TableCell>Traffic</TableCell>
                <TableCell>Backlinks</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredReports.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      {searchTerm ? 'No reports found matching your search' : 'No reports available'}
                    </Typography>
                    {!searchTerm && (
                      <Button
                        variant="outlined"
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
                filteredReports.map((report) => (
                  <TableRow key={report.domain_name} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
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
                      <Typography variant="body2">
                        {formatNumber(report.data_for_seo_metrics?.domain_rating_dr)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatNumber(report.data_for_seo_metrics?.organic_traffic_est)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatNumber(report.data_for_seo_metrics?.total_backlinks)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                        <Tooltip title="View Report">
                          <IconButton
                            size="small"
                            onClick={() => handleViewReport(report.domain_name)}
                          >
                            <VisibilityIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete Report">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteClick(report.domain_name)}
                            disabled={deleteMutation.isPending}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        {filteredReports.length > 0 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <Pagination
              count={Math.ceil((reports?.length || 0) / limit)}
              page={page}
              onChange={handlePageChange}
              color="primary"
            />
          </Box>
        )}
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Report</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the analysis report for{' '}
            <strong>{domainToDelete}</strong>? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
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
    </Box>
  );
};

export default ReportsListPage;
