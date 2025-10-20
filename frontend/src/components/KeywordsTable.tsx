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
} from '@mui/material';
import {
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  People as PeopleIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

import { useApi, OrganicKeyword } from '../services/api';

interface KeywordsTableProps {
  domain: string;
}

const KeywordsTable: React.FC<KeywordsTableProps> = ({ domain }) => {
  const api = useApi();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');

  const {
    data: keywordsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['keywords', domain, page * rowsPerPage, rowsPerPage],
    queryFn: () => api.getKeywords(domain, rowsPerPage, page * rowsPerPage),
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

  const formatCurrency = (num: number | undefined) => {
    if (num === undefined || num === null) return 'N/A';
    return `$${num.toFixed(2)}`;
  };

  const formatPercentage = (num: number | undefined) => {
    if (num === undefined || num === null) return 'N/A';
    return `${(num * 100).toFixed(1)}%`;
  };

  const getCompetitionColor = (competition: number | undefined) => {
    if (competition === undefined || competition === null) return 'default';
    if (competition < 0.3) return 'success';
    if (competition < 0.7) return 'warning';
    return 'error';
  };

  const getCompetitionLabel = (competition: number | undefined) => {
    if (competition === undefined || competition === null) return 'N/A';
    if (competition < 0.3) return 'Low';
    if (competition < 0.7) return 'Medium';
    return 'High';
  };

  // Filter keywords based on search term
  const filteredKeywords = keywordsData?.keywords?.filter((keyword) =>
    keyword.keyword.toLowerCase().includes(searchTerm.toLowerCase())
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
        Failed to load keywords: {error.message}
      </Alert>
    );
  }

  if (!keywordsData || !keywordsData.keywords || keywordsData.keywords.length === 0) {
    return (
      <Alert severity="info">
        No keywords data available for this domain.
      </Alert>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Organic Keywords ({formatNumber(keywordsData.total_count)})
        </Typography>
        <TextField
          placeholder="Search keywords..."
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
          sx={{ minWidth: 250 }}
        />
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Keyword</TableCell>
              <TableCell align="right">Rank</TableCell>
              <TableCell align="right">Search Volume</TableCell>
              <TableCell align="right">Traffic Share</TableCell>
              <TableCell align="right">CPC</TableCell>
              <TableCell align="center">Competition</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredKeywords.map((keyword, index) => (
              <TableRow key={index} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {keyword.keyword}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    <TrendingUpIcon color="primary" fontSize="small" />
                    <Typography variant="body2">
                      {formatNumber(keyword.rank)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    <PeopleIcon color="info" fontSize="small" />
                    <Typography variant="body2">
                      {formatNumber(keyword.search_volume)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatPercentage(keyword.traffic_share)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    <AttachMoneyIcon color="success" fontSize="small" />
                    <Typography variant="body2">
                      {formatCurrency(keyword.cpc)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="center">
                  <Chip
                    label={getCompetitionLabel(keyword.competition)}
                    color={getCompetitionColor(keyword.competition) as any}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[10, 25, 50, 100]}
        component="div"
        count={keywordsData.total_count}
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

export default KeywordsTable;
