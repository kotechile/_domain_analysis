import React, { useState } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TablePagination,
  TextField,
  InputAdornment,
  Chip,
  CircularProgress,
  Alert,
  Link,
  Tooltip,
} from '@mui/material';
import {
  Search as SearchIcon,
  Link as LinkIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

import { useApi, ReferringDomain } from '../services/api';

interface BacklinksTableProps {
  domain: string;
}

const BacklinksTable: React.FC<BacklinksTableProps> = ({ domain }) => {
  const api = useApi();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');

  const {
    data: backlinksData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['backlinks', domain, page * rowsPerPage, rowsPerPage],
    queryFn: () => api.getBacklinks(domain, rowsPerPage, page * rowsPerPage),
  });

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null) return 'N/A';
    return num.toLocaleString();
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const getDomainRankColor = (rank: number | undefined) => {
    if (rank === undefined || rank === null) return 'default';
    if (rank >= 70) return 'success';
    if (rank >= 40) return 'warning';
    return 'error';
  };

  const getDomainRankLabel = (rank: number | undefined) => {
    if (rank === undefined || rank === null) return 'N/A';
    if (rank >= 70) return 'High';
    if (rank >= 40) return 'Medium';
    return 'Low';
  };

  // Filter backlinks based on search term
  const filteredBacklinks = backlinksData?.backlinks?.filter((backlink) =>
    backlink.domain.toLowerCase().includes(searchTerm.toLowerCase()) ||
    backlink.anchor_text.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        Failed to load backlinks: {error.message}
      </Alert>
    );
  }

  if (!backlinksData || !backlinksData.backlinks || backlinksData.backlinks.length === 0) {
    return (
      <Alert severity="info">
        No backlinks data available for this domain.
      </Alert>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Referring Domains ({formatNumber(backlinksData.total_count)})
        </Typography>
        <TextField
          placeholder="Search domains or anchor text..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 300 }}
        />
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Referring Domain</TableCell>
              <TableCell align="center">Domain Rank</TableCell>
              <TableCell align="right">Backlinks</TableCell>
              <TableCell>Anchor Text</TableCell>
              <TableCell align="center">First Seen</TableCell>
              <TableCell align="center">Last Seen</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredBacklinks.map((backlink, index) => (
              <TableRow key={index} hover>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinkIcon color="primary" fontSize="small" />
                    <Typography variant="body2" fontWeight="medium">
                      {backlink.domain}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="center">
                  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="body2" fontWeight="medium">
                      {formatNumber(backlink.domain_rank)}
                    </Typography>
                    <Chip
                      label={getDomainRankLabel(backlink.domain_rank)}
                      color={getDomainRankColor(backlink.domain_rank) as any}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    <TrendingUpIcon color="info" fontSize="small" />
                    <Typography variant="body2">
                      {formatNumber(backlink.backlinks_count)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Tooltip title={backlink.anchor_text} arrow>
                    <Typography
                      variant="body2"
                      sx={{
                        maxWidth: 200,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {backlink.anchor_text || 'N/A'}
                    </Typography>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                    <ScheduleIcon color="action" fontSize="small" />
                    <Typography variant="body2">
                      {formatDate(backlink.first_seen)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="center">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                    <ScheduleIcon color="action" fontSize="small" />
                    <Typography variant="body2">
                      {formatDate(backlink.last_seen)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Visit Domain">
                    <Link
                      href={`https://${backlink.domain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ textDecoration: 'none' }}
                    >
                      <OpenInNewIcon fontSize="small" color="action" />
                    </Link>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[10, 25, 50, 100]}
        component="div"
        count={backlinksData.total_count}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        labelRowsPerPage="Rows per page:"
        labelDisplayedRows={({ from, to, count }) =>
          `${from}-${to} of ${count !== -1 ? count : `more than ${to}`}`
        }
      />
    </Box>
  );
};

export default BacklinksTable;
