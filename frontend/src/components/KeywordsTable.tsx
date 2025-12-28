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
  Button,
} from '@mui/material';
import {
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  People as PeopleIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

import { useApi } from '../services/api';
import { exportKeywordsToCSV, KeywordExportData } from '../utils/csvExport';

interface KeywordsTableProps {
  domain: string;
  reportData?: {
    data_for_seo_metrics?: {
      total_keywords?: number;
    };
    detailed_data_available?: {
      backlinks?: boolean;
      keywords?: boolean;
      referring_domains?: boolean;
    };
  };
  keywordMetrics?: {
    total_keywords: number;
    avg_position_top_10: number;
    total_search_volume: number;
    keyword_diversity: number;
  };
}

const KeywordsTable: React.FC<KeywordsTableProps> = ({ domain, reportData, keywordMetrics }) => {
  const api = useApi();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  // Detailed data is now loaded automatically during analysis

  const {
    data: keywordsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['keywords', domain, page * rowsPerPage, rowsPerPage],
    queryFn: () => api.getKeywords(domain, rowsPerPage, page * rowsPerPage),
    enabled: true, // Always load since data is available after analysis
    retry: (failureCount, error) => {
      // Don't retry on 404 errors (no data available)
      if (error?.message?.includes('404') || error?.message?.includes('not found')) {
        return false;
      }
      return failureCount < 3;
    },
  });

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleExportCSV = async () => {
    try {
      setIsExporting(true);
      const exportData = await api.exportKeywords(domain);
      
      // Convert to export format
      const keywordsForExport: KeywordExportData[] = exportData.keywords.map(keyword => ({
        keyword: keyword.keyword,
        rank: keyword.rank,
        search_volume: keyword.search_volume,
        traffic_share: keyword.traffic_share,
        cpc: keyword.cpc,
        competition: keyword.competition,
        etv: keyword.etv,
        url: keyword.url,
        title: keyword.title,
        description: keyword.description,
        keyword_difficulty: keyword.keyword_difficulty
      }));
      
      exportKeywordsToCSV(keywordsForExport, domain);
    } catch (error) {
      console.error('Failed to export keywords:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`Failed to export keywords: ${errorMessage}`);
    } finally {
      setIsExporting(false);
    }
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

  const getCompetitionValue = (keyword: any): number | undefined => {
    // Try to get competition as a number first
    const competitionNumber = keyword.keyword_data?.keyword_info?.competition;
    if (typeof competitionNumber === 'number') {
      return competitionNumber;
    }
    
    // If not available, try to convert competition_level string to number
    const competitionLevel = keyword.keyword_data?.keyword_info?.competition_level;
    if (typeof competitionLevel === 'string') {
      // Map string values to numbers
      const levelMap: { [key: string]: number } = {
        'low': 0.2,
        'medium': 0.5,
        'high': 0.8,
        'very_high': 0.9
      };
      return levelMap[competitionLevel.toLowerCase()] || 0.5;
    }
    
    return undefined;
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
        <CircularProgress />
        <Typography variant="body2" sx={{ ml: 2 }}>
          Loading detailed keywords data...
        </Typography>
      </Box>
    );
  }

  if (error) {
    // Check if it's a 404 error (no data available) vs other errors
    if (error.message?.includes('404') || error.message?.includes('not found')) {
      return (
        <Alert severity="info">
          No detailed keywords data available for this domain. The analysis may not have collected detailed keywords data.
        </Alert>
      );
    }
    
    return (
      <Alert severity="error">
        Failed to load keywords: {error.message}
      </Alert>
    );
  }

  // Filter and validate keywords first - only include keywords with actual keyword text
  const validKeywords = keywordsData?.keywords?.filter((keyword) => {
    const keywordText = keyword.keyword_data?.keyword;
    return keywordText && keywordText.trim() !== '' && keywordText !== 'N/A';
  }) || [];
  
  // Validate that we actually have valid keywords before displaying
  const hasValidKeywords = validKeywords.length > 0;
  const displayedTotalCount = keywordsData?.total_count || 0;
  
  // Use actual count of valid keywords, not misleading total_count
  const validTotalCount = hasValidKeywords ? validKeywords.length : 0;

  if (!keywordsData || !hasValidKeywords) {
    return (
      <Alert severity="info">
        No keywords data available for this domain. The analysis may not have collected detailed keywords data.
      </Alert>
    );
  }

  // Filter valid keywords based on search term
  const filteredKeywords = validKeywords.filter((keyword) => {
    if (!searchTerm) return true; // Show all valid keywords if no search term
    const keywordText = keyword.keyword_data?.keyword || '';
    return keywordText.toLowerCase().includes(searchTerm.toLowerCase());
  });

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Organic Keywords ({formatNumber(validTotalCount)})
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
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
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExportCSV}
            disabled={isExporting || !keywordsData?.keywords?.length}
            size="small"
          >
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </Button>
        </Box>
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
            {filteredKeywords.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary">
                    No keywords match your search criteria.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredKeywords.map((keyword, index) => (
              <TableRow key={index} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {keyword.keyword_data?.keyword || 'N/A'}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    <TrendingUpIcon color="primary" fontSize="small" />
                    <Typography variant="body2">
                      {formatNumber(keyword.ranked_serp_element?.serp_item?.rank_absolute || 0)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    <PeopleIcon color="info" fontSize="small" />
                    <Typography variant="body2">
                      {formatNumber(keyword.keyword_data?.keyword_info?.search_volume || 0)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatPercentage(keyword.ranked_serp_element?.serp_item?.etv || 0)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    <AttachMoneyIcon color="success" fontSize="small" />
                    <Typography variant="body2">
                      {formatCurrency(keyword.keyword_data?.keyword_info?.cpc || 0)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="center">
                  <Chip
                    label={getCompetitionLabel(getCompetitionValue(keyword))}
                    color={getCompetitionColor(getCompetitionValue(keyword)) as any}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
              </TableRow>
            ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[10, 25, 50, 100]}
        component="div"
        count={validTotalCount}
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
