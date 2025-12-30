import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Box,
  Typography,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Button,
  TextField,
  InputAdornment,
  Pagination,
  Stack,
  Grid,
  useTheme,
} from '@mui/material';
import {
  Search as SearchIcon,
  CheckCircle as CheckCircleIcon,
  Clear as ClearIcon,
  FilterList as FilterListIcon,
} from '@mui/icons-material';
import { Auction, BulkPageSummaryResult } from '../services/api';

interface AuctionsTableProps {
  auctions: Auction[];
  onSort?: (field: string, order: 'asc' | 'desc') => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSearch?: (searchTerm: string) => void;
  onFilterChange?: (filters: {
    preferred?: boolean;
    auctionSite?: string;
    tld?: string;
    hasStatistics?: boolean;
    scored?: boolean;
    minRank?: number;
    maxRank?: number;
    minScore?: number;
    maxScore?: number;
  }) => void;
  totalCount?: number;
  hasMore?: boolean;
  page?: number;
  onPageChange?: (page: number) => void;
  pageSize?: number;
  availableTlds?: string[];
}

const AuctionsTable: React.FC<AuctionsTableProps> = ({
  auctions,
  onSort,
  sortBy = 'expiration_date',
  sortOrder = 'asc',
  onSearch,
  onFilterChange,
  totalCount = 0,
  hasMore = false,
  page = 0,
  onPageChange,
  pageSize = 50,
  availableTlds = [],
}) => {
  const theme = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [preferredFilter, setPreferredFilter] = useState<boolean | undefined>(undefined);
  const [auctionSiteFilter, setAuctionSiteFilter] = useState<string>('');
  const [tldFilter, setTldFilter] = useState<string>('');
  const [hasStatisticsFilter, setHasStatisticsFilter] = useState<boolean | undefined>(undefined);
  const [scoredFilter, setScoredFilter] = useState<boolean | undefined>(undefined);
  const [minRankFilter, setMinRankFilter] = useState<string>('');
  const [maxRankFilter, setMaxRankFilter] = useState<string>('');
  const [minScoreFilter, setMinScoreFilter] = useState<string>('');
  const [maxScoreFilter, setMaxScoreFilter] = useState<string>('');

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setSearchTerm(value);
    if (onSearch) {
      onSearch(value);
    }
  };

  const handlePreferredFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.checked ? true : undefined;
    setPreferredFilter(newValue);
    applyAllFilters({ preferred: newValue });
  };

  const handleAuctionSiteFilterChange = (event: any) => {
    const newValue = event.target.value;
    setAuctionSiteFilter(newValue);
    applyAllFilters({ auctionSite: newValue === '' ? undefined : newValue });
  };

  const handleTldFilterChange = (event: any) => {
    const newValue = event.target.value;
    setTldFilter(newValue);
    applyAllFilters({ tld: newValue === '' ? undefined : newValue });
  };

  const handleHasStatisticsFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.checked ? true : undefined;
    setHasStatisticsFilter(newValue);
    applyAllFilters({ hasStatistics: newValue });
  };

  const handleScoredFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.checked ? true : undefined;
    setScoredFilter(newValue);
    applyAllFilters({ scored: newValue });
  };

  const handleRankFilterChange = () => {
    applyFilters();
  };

  const handleScoreFilterChange = () => {
    applyFilters();
  };

  const applyAllFilters = (overrides: {
    preferred?: boolean | undefined;
    auctionSite?: string | undefined;
    tld?: string | undefined;
    hasStatistics?: boolean | undefined;
    scored?: boolean | undefined;
  } = {}) => {
    if (!onFilterChange) return;
    
    const filterObj: {
      preferred?: boolean;
      auctionSite?: string;
      tld?: string;
      hasStatistics?: boolean;
      scored?: boolean;
      minRank?: number;
      maxRank?: number;
      minScore?: number;
      maxScore?: number;
    } = {};
    
    const preferred = overrides.preferred !== undefined ? overrides.preferred : preferredFilter;
    if (preferred !== undefined) {
      filterObj.preferred = preferred;
    }
    
    const auctionSite = overrides.auctionSite !== undefined ? overrides.auctionSite : auctionSiteFilter;
    if (auctionSite && auctionSite !== '') {
      filterObj.auctionSite = auctionSite;
    }
    
    const tld = overrides.tld !== undefined ? overrides.tld : tldFilter;
    if (tld && tld !== '') {
      filterObj.tld = tld;
    }
    
    const hasStatistics = overrides.hasStatistics !== undefined ? overrides.hasStatistics : hasStatisticsFilter;
    if (hasStatistics !== undefined) {
      filterObj.hasStatistics = hasStatistics;
    }
    
    const scored = overrides.scored !== undefined ? overrides.scored : scoredFilter;
    if (scored !== undefined) {
      filterObj.scored = scored;
    }
    
    const minRank = minRankFilter ? parseInt(minRankFilter) : undefined;
    if (minRank !== undefined && !isNaN(minRank)) filterObj.minRank = minRank;
    
    const maxRank = maxRankFilter ? parseInt(maxRankFilter) : undefined;
    if (maxRank !== undefined && !isNaN(maxRank)) filterObj.maxRank = maxRank;
    
    const minScore = minScoreFilter ? parseFloat(minScoreFilter) : undefined;
    if (minScore !== undefined && !isNaN(minScore)) filterObj.minScore = minScore;
    
    const maxScore = maxScoreFilter ? parseFloat(maxScoreFilter) : undefined;
    if (maxScore !== undefined && !isNaN(maxScore)) filterObj.maxScore = maxScore;
    
    onFilterChange(filterObj);
  };

  const applyFilters = () => {
    applyAllFilters();
  };

  const handleClearFilters = () => {
    setPreferredFilter(undefined);
    setAuctionSiteFilter('');
    setTldFilter('');
    setHasStatisticsFilter(undefined);
    setScoredFilter(undefined);
    setMinRankFilter('');
    setMaxRankFilter('');
    setMinScoreFilter('');
    setMaxScoreFilter('');
    setSearchTerm('');
    if (onFilterChange) {
      onFilterChange({});
    }
    if (onSearch) {
      onSearch('');
    }
  };

  const handleSort = (field: string) => {
    if (!onSort) return;
    const newOrder = sortBy === field && sortOrder === 'asc' ? 'desc' : 'asc';
    onSort(field, newOrder);
  };

  const formatNumber = (num?: number): string => {
    if (num === undefined || num === null) return '-';
    return num.toLocaleString();
  };

  const formatDate = (dateStr?: string): string => {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  const getStatisticsValue = (statistics: BulkPageSummaryResult | undefined, field: string): number | undefined => {
    if (!statistics) return undefined;
    return (statistics as any)[field];
  };

  const hasActiveFilters = 
    preferredFilter !== undefined ||
    auctionSiteFilter !== '' ||
    tldFilter !== '' ||
    hasStatisticsFilter !== undefined ||
    scoredFilter !== undefined ||
    minRankFilter !== '' ||
    maxRankFilter !== '' ||
    minScoreFilter !== '' ||
    maxScoreFilter !== '';

  const auctionSites = Array.from(new Set(auctions.map(a => a.auction_site))).sort();
  
  const tlds = availableTlds.length > 0 
    ? availableTlds 
    : (() => {
        const extractTld = (domain: string): string => {
          const parts = domain.split('.');
          if (parts.length > 1) {
            return '.' + parts[parts.length - 1];
          }
          return '';
        };
        return Array.from(new Set(auctions.map(a => extractTld(a.domain)))).filter(tld => tld).sort();
      })();

  const SortableHeader: React.FC<{ field: string; label: string }> = ({ field, label }) => (
    <TableCell>
      {onSort ? (
        <TableSortLabel
          active={sortBy === field}
          direction={sortBy === field ? sortOrder : 'asc'}
          onClick={() => handleSort(field)}
          sx={{
            '& .MuiTableSortLabel-icon': {
              opacity: sortBy === field ? 1 : 0.5,
            },
          }}
        >
          {label}
        </TableSortLabel>
      ) : (
        label
      )}
    </TableCell>
  );

  if (auctions.length === 0) {
    return (
      <Paper variant="outlined" sx={{ p: 6, textAlign: 'center', borderRadius: 2 }}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No auctions found
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload a CSV file to get started.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Search and Filters */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <FilterListIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Filters & Search
          </Typography>
          {hasActiveFilters && (
            <Chip
              label={`${Object.values({
                preferred: preferredFilter,
                auctionSite: auctionSiteFilter,
                tld: tldFilter,
                hasStatistics: hasStatisticsFilter,
                scored: scoredFilter,
                minRank: minRankFilter,
                maxRank: maxRankFilter,
                minScore: minScoreFilter,
                maxScore: maxScoreFilter,
              }).filter(v => v !== undefined && v !== '').length} active`}
              size="small"
              color="primary"
              sx={{ ml: 2 }}
            />
          )}
        </Box>

        <Stack spacing={3}>
          {onSearch && (
            <TextField
              fullWidth
              placeholder="Search domains..."
              value={searchTerm}
              onChange={handleSearchChange}
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
          )}

          {onFilterChange && (
            <>
              {/* Quick Filters */}
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={preferredFilter === true}
                        onChange={handlePreferredFilterChange}
                        color="primary"
                      />
                    }
                    label="Preferred Only"
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={scoredFilter === true}
                        onChange={handleScoredFilterChange}
                        color="primary"
                      />
                    }
                    label="Scored Only"
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={hasStatisticsFilter === true}
                        onChange={handleHasStatisticsFilterChange}
                        color="primary"
                      />
                    }
                    label="With Statistics"
                  />
                </Grid>
              </Grid>

              {/* Dropdown Filters */}
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Auction Site</InputLabel>
                    <Select
                      value={auctionSiteFilter}
                      onChange={handleAuctionSiteFilterChange}
                      label="Auction Site"
                    >
                      <MenuItem value="">
                        <em>All Sites</em>
                      </MenuItem>
                      {auctionSites.map((site) => (
                        <MenuItem key={site} value={site}>
                          {site}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Extension</InputLabel>
                    <Select
                      value={tldFilter}
                      onChange={handleTldFilterChange}
                      label="Extension"
                    >
                      <MenuItem value="">
                        <em>All TLDs</em>
                      </MenuItem>
                      {tlds.map((tld) => (
                        <MenuItem key={tld} value={tld}>
                          {tld}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              {/* Range Filters */}
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm="auto">
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                    Ranking Range:
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Min Rank"
                    type="number"
                    value={minRankFilter}
                    onChange={(e) => setMinRankFilter(e.target.value)}
                    onBlur={handleRankFilterChange}
                    inputProps={{ min: 1 }}
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Max Rank"
                    type="number"
                    value={maxRankFilter}
                    onChange={(e) => setMaxRankFilter(e.target.value)}
                    onBlur={handleRankFilterChange}
                    inputProps={{ min: 1 }}
                  />
                </Grid>

                <Grid item xs={12} sm="auto">
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                    Score Range:
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Min Score"
                    type="number"
                    value={minScoreFilter}
                    onChange={(e) => setMinScoreFilter(e.target.value)}
                    onBlur={handleScoreFilterChange}
                    inputProps={{ min: 0, max: 100, step: 0.1 }}
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Max Score"
                    type="number"
                    value={maxScoreFilter}
                    onChange={(e) => setMaxScoreFilter(e.target.value)}
                    onBlur={handleScoreFilterChange}
                    inputProps={{ min: 0, max: 100, step: 0.1 }}
                  />
                </Grid>
              </Grid>

              {hasActiveFilters && (
                <Box>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleClearFilters}
                    startIcon={<ClearIcon />}
                    sx={{ borderRadius: 2 }}
                  >
                    Clear All Filters
                  </Button>
                </Box>
              )}
            </>
          )}
        </Stack>
      </Paper>

      {/* Results Info */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Showing <strong>{auctions.length}</strong> of <strong>{totalCount.toLocaleString()}</strong> auctions
        </Typography>
        {sortBy && (
          <Chip
            label={`Sorted by: ${sortBy} (${sortOrder})`}
            size="small"
            variant="outlined"
          />
        )}
      </Box>

      {/* Table */}
      <TableContainer 
        component={Paper} 
        variant="outlined"
        sx={{ 
          maxHeight: '70vh', 
          overflowX: 'auto',
          borderRadius: 2,
        }}
      >
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <SortableHeader field="domain" label="Domain" />
              <SortableHeader field="expiration_date" label="Expiration Date" />
              <TableCell>Auction Site</TableCell>
              <SortableHeader field="score" label="Score" />
              <SortableHeader field="ranking" label="Ranking" />
              <TableCell>Preferred</TableCell>
              <TableCell>Has Statistics</TableCell>
              <TableCell>Rank</TableCell>
              <TableCell>Backlinks</TableCell>
              <TableCell>Referring Domains</TableCell>
              <TableCell>Main Domains</TableCell>
              <TableCell>Spam Score</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {auctions.map((auction) => {
              const stats = auction.statistics;
              const hasStats = !!stats;

              return (
                <TableRow 
                  key={auction.id} 
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
                      {auction.domain}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatDate(auction.expiration_date)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={auction.auction_site} 
                      size="small" 
                      variant="outlined"
                      sx={{ borderRadius: 1 }}
                    />
                  </TableCell>
                  <TableCell>
                    {auction.score !== undefined && auction.score !== null ? (
                      <Chip
                        label={Number(auction.score).toFixed(2)}
                        size="small"
                        color="primary"
                        sx={{ fontWeight: 600, borderRadius: 1 }}
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">-</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {auction.ranking !== undefined && auction.ranking !== null ? (
                      <Chip
                        label={`#${auction.ranking}`}
                        size="small"
                        variant="outlined"
                        sx={{ borderRadius: 1 }}
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">-</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {auction.preferred ? (
                      <Chip
                        label="Preferred"
                        color="success"
                        size="small"
                        icon={<CheckCircleIcon />}
                        sx={{ borderRadius: 1 }}
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">-</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={hasStats ? "Yes" : "No"} 
                      color={hasStats ? "success" : "default"} 
                      size="small"
                      sx={{ borderRadius: 1 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatNumber(getStatisticsValue(stats, 'rank'))}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatNumber(getStatisticsValue(stats, 'backlinks'))}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatNumber(getStatisticsValue(stats, 'referring_domains'))}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatNumber(getStatisticsValue(stats, 'referring_main_domains'))}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatNumber(getStatisticsValue(stats, 'backlinks_spam_score'))}
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalCount > pageSize && onPageChange && (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 4, gap: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Page {page + 1} of {Math.ceil(totalCount / pageSize)} ({totalCount.toLocaleString()} total records)
          </Typography>
          <Pagination
            count={Math.ceil(totalCount / pageSize)}
            page={page + 1}
            onChange={(_, value) => onPageChange(value - 1)}
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
    </Box>
  );
};

export default AuctionsTable;










