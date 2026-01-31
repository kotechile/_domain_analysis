import React, { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Checkbox,
  TextField,
  InputAdornment,
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
} from '@mui/material';
import {
  Search as SearchIcon,
} from '@mui/icons-material';

export interface NamecheapDomain {
  id: string;
  url?: string;
  name: string;
  start_date?: string;
  end_date?: string;
  price?: number;
  start_price?: number;
  renew_price?: number;
  bid_count?: number;
  ahrefs_domain_rating?: number;
  umbrella_ranking?: number;
  cloudflare_ranking?: number;
  estibot_value?: number;
  extensions_taken?: number;
  keyword_search_count?: number;
  registered_date?: string;
  last_sold_price?: number;
  last_sold_year?: number;
  is_partner_sale?: boolean;
  semrush_a_score?: number;
  majestic_citation?: number;
  ahrefs_backlinks?: number;
  semrush_backlinks?: number;
  majestic_backlinks?: number;
  majestic_trust_flow?: number;
  go_value?: number;
  created_at?: string;
  updated_at?: string;
  // Scoring fields
  filter_status?: 'PASS' | 'FAIL';
  filter_reason?: string;
  total_meaning_score?: number;
  age_score?: number;
  lexical_frequency_score?: number;
  semantic_value_score?: number;
  rank?: number;
}

interface NamecheapDomainTableProps {
  domains: NamecheapDomain[];
  selectedDomains: Set<string>;
  onSelectionChange: (selected: Set<string>) => void;
  onSort?: (field: string, order: 'asc' | 'desc') => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSearch?: (searchTerm: string) => void;
  onFilterChange?: (filters: {
    extensions?: string[];
    noSpecialChars?: boolean;
    noNumbers?: boolean;
    filterStatus?: 'PASS' | 'FAIL' | 'ALL';
  }) => void;
  hasData?: boolean; // Indicates if any data exists (not just filtered results)
  domainCounts?: { passed: number; failed: number; total: number }; // Total counts for filter buttons
  initialFilterStatus?: 'PASS' | 'FAIL' | 'ALL'; // Initial filter status from parent
}

const NamecheapDomainTable: React.FC<NamecheapDomainTableProps> = ({
  domains,
  selectedDomains,
  onSelectionChange,
  onSort,
  sortBy = 'name',
  sortOrder = 'asc',
  onSearch,
  onFilterChange,
  hasData = false,
  domainCounts,
  initialFilterStatus = 'ALL',
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedExtensions, setSelectedExtensions] = useState<string[]>([]);
  const [noSpecialChars, setNoSpecialChars] = useState(false);
  const [noNumbers, setNoNumbers] = useState(false);
  const [filterStatus, setFilterStatus] = useState<'PASS' | 'FAIL' | 'ALL'>(initialFilterStatus);
  
  // Sync filterStatus when initialFilterStatus changes
  useEffect(() => {
    if (initialFilterStatus && initialFilterStatus !== filterStatus) {
      setFilterStatus(initialFilterStatus);
    }
  }, [initialFilterStatus]);
  

  const commonExtensions = ['.com', '.net', '.org', '.ai', '.io', '.co', '.xyz', '.app', '.dev', '.tech'];

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const allIds = new Set(domains.map(d => d.id));
      onSelectionChange(allIds);
    } else {
      onSelectionChange(new Set());
    }
  };

  const handleSelectRow = (domainId: string) => {
    const newSelected = new Set(selectedDomains);
    if (newSelected.has(domainId)) {
      newSelected.delete(domainId);
    } else {
      newSelected.add(domainId);
    }
    onSelectionChange(newSelected);
  };

  const handleSort = (field: string) => {
    if (!onSort) return;
    const newOrder = sortBy === field && sortOrder === 'asc' ? 'desc' : 'asc';
    onSort(field, newOrder);
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setSearchTerm(value);
    if (onSearch) {
      onSearch(value);
    }
  };

  const handleExtensionChange = (event: any) => {
    const value = event.target.value;
    const newExtensions = typeof value === 'string' ? value.split(',') : value;
    
    // Filter out the "__ALL__" marker if present
    const filteredExtensions = newExtensions.filter((ext: string) => ext !== '__ALL__');
    
    // If "__ALL__" was selected or no extensions selected, clear the filter
    if (newExtensions.includes('__ALL__') || filteredExtensions.length === 0) {
      setSelectedExtensions([]);
      if (onFilterChange) {
        onFilterChange({
          extensions: undefined,
          noSpecialChars,
          noNumbers,
          filterStatus,
        });
      }
    } else {
      setSelectedExtensions(filteredExtensions);
      if (onFilterChange) {
        onFilterChange({
          extensions: filteredExtensions,
          noSpecialChars,
          noNumbers,
          filterStatus,
        });
      }
    }
  };

  const handleNoSpecialCharsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.checked;
    setNoSpecialChars(value);
    if (onFilterChange) {
      onFilterChange({
        extensions: selectedExtensions,
        noSpecialChars: value,
        noNumbers,
        filterStatus,
      });
    }
  };

  const handleNoNumbersChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.checked;
    setNoNumbers(value);
    if (onFilterChange) {
      onFilterChange({
        extensions: selectedExtensions,
        noSpecialChars,
        noNumbers: value,
        filterStatus,
      });
    }
  };

  const handleFilterStatusChange = (status: 'PASS' | 'FAIL' | 'ALL') => {
    setFilterStatus(status);
    if (onFilterChange) {
      onFilterChange({
        extensions: selectedExtensions,
        noSpecialChars,
        noNumbers,
        filterStatus: status,
      });
    }
  };

  const handleClearFilters = () => {
    setSelectedExtensions([]);
    setNoSpecialChars(false);
    setNoNumbers(false);
    setFilterStatus('ALL');
    if (onFilterChange) {
      onFilterChange({
        extensions: undefined,
        noSpecialChars: false,
        noNumbers: false,
        filterStatus: 'ALL',
      });
    }
  };

  const hasActiveFilters = (selectedExtensions && selectedExtensions.length > 0) || noSpecialChars || noNumbers || filterStatus !== 'ALL';

  const formatNumber = (num?: number): string => {
    if (num === undefined || num === null) return '-';
    return num.toLocaleString();
  };

  const formatCurrency = (num?: number): string => {
    if (num === undefined || num === null) return '-';
    return `$${num.toFixed(2)}`;
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

  const formatBoolean = (value?: boolean): string => {
    if (value === undefined || value === null) return '-';
    return value ? 'Yes' : 'No';
  };

  const isAllSelected = domains.length > 0 && selectedDomains.size === domains.length;
  const isIndeterminate = selectedDomains.size > 0 && selectedDomains.size < domains.length;

  const SortableHeader: React.FC<{ field: string; label: string }> = ({ field, label }) => (
    <TableCell>
      {onSort ? (
        <TableSortLabel
          active={sortBy === field}
          direction={sortBy === field ? sortOrder : 'asc'}
          onClick={() => handleSort(field)}
        >
          {label}
        </TableSortLabel>
      ) : (
        label
      )}
    </TableCell>
  );

  // Show "no data" message only if no data has been loaded at all
  if (!hasData && domains.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No Namecheap domains loaded. Upload a CSV file to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Search Bar and Filters */}
      <Box sx={{ mb: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
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
          />
        )}
        
        {/* Filter Controls */}
        {onFilterChange && hasData && (
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Extensions</InputLabel>
              <Select
                multiple
                value={selectedExtensions}
                onChange={handleExtensionChange}
                label="Extensions"
                renderValue={(selected) => {
                  if (selected.length === 0) return 'All Extensions';
                  return (selected as string[]).join(', ');
                }}
              >
                <MenuItem value="__ALL__" key="__ALL__">
                  <em>All Extensions</em>
                </MenuItem>
                {commonExtensions.map((ext) => (
                  <MenuItem key={ext} value={ext}>
                    {ext}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControlLabel
              control={
                <Switch
                  checked={noSpecialChars}
                  onChange={handleNoSpecialCharsChange}
                />
              }
              label="No Special Characters"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={noNumbers}
                  onChange={handleNoNumbersChange}
                />
              }
              label="No Numbers"
            />
            
            {/* Filter Status Buttons */}
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', ml: 2 }}>
              <Typography variant="body2" sx={{ mr: 1, fontWeight: 'medium' }}>Show:</Typography>
              <Button
                variant={filterStatus === 'PASS' ? "contained" : "outlined"}
                color={filterStatus === 'PASS' ? "success" : "inherit"}
                size="small"
                onClick={() => handleFilterStatusChange('PASS')}
                sx={{ 
                  fontWeight: filterStatus === 'PASS' ? 'bold' : 'normal',
                  minWidth: 120
                }}
              >
                Passed {domainCounts && `(${domainCounts.passed})`}
              </Button>
              <Button
                variant={filterStatus === 'FAIL' ? "contained" : "outlined"}
                color={filterStatus === 'FAIL' ? "error" : "inherit"}
                size="small"
                onClick={() => handleFilterStatusChange('FAIL')}
                sx={{ 
                  fontWeight: filterStatus === 'FAIL' ? 'bold' : 'normal',
                  minWidth: 120
                }}
              >
                Failed {domainCounts && `(${domainCounts.failed})`}
              </Button>
              <Button
                variant={filterStatus === 'ALL' ? "contained" : "outlined"}
                size="small"
                onClick={() => handleFilterStatusChange('ALL')}
                sx={{ 
                  fontWeight: filterStatus === 'ALL' ? 'bold' : 'normal',
                  minWidth: 80
                }}
              >
                All
              </Button>
            </Box>
            
            <Button
              variant={hasActiveFilters ? "contained" : "outlined"}
              size="small"
              onClick={handleClearFilters}
              disabled={!hasActiveFilters}
              sx={{ ml: 'auto' }}
            >
              {hasActiveFilters ? 'Clear Filters' : 'No Filters'}
            </Button>
          </Box>
        )}
      </Box>

      {/* Selection Info */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Chip
          label={`${selectedDomains.size} selected`}
          color="primary"
          variant="outlined"
        />
        <Typography variant="body2" color="text.secondary">
          {hasActiveFilters 
            ? `Showing ${domains.length} domain(s) (filtered)`
            : `Total domains: ${domains.length}`
          }
          {domains.length > 0 && (
            <> | Passed: {domains.filter(d => d.filter_status === 'PASS').length}, Failed: {domains.filter(d => d.filter_status === 'FAIL').length}</>
          )}
        </Typography>
      </Box>

      {/* Show message if filters return no results */}
      {hasData && domains.length === 0 && hasActiveFilters && (
        <Box sx={{ p: 4, textAlign: 'center', border: '1px dashed', borderColor: 'divider', borderRadius: 2 }}>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
            No domains match the current filters
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Try adjusting your filters or clear them to see all domains
          </Typography>
          <Button
            variant="contained"
            color="primary"
            size="large"
            onClick={handleClearFilters}
          >
            Show All Domains
          </Button>
        </Box>
      )}

      {domains.length > 0 && (
        <TableContainer component={Paper} sx={{ maxHeight: '70vh', overflowX: 'auto' }}>
          <Table stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  indeterminate={isIndeterminate}
                  checked={isAllSelected}
                  onChange={handleSelectAll}
                />
              </TableCell>
              <SortableHeader field="name" label="Domain Name" />
              <SortableHeader field="total_meaning_score" label="Score" />
              <SortableHeader field="rank" label="Rank" />
              <TableCell>Filter Status</TableCell>
              <SortableHeader field="price" label="Price" />
              <SortableHeader field="end_date" label="End Date" />
              <SortableHeader field="ahrefs_domain_rating" label="Ahrefs DR" />
              <SortableHeader field="estibot_value" label="Estibot Value" />
              <SortableHeader field="keyword_search_count" label="Keyword Search" />
              <SortableHeader field="last_sold_year" label="Last Sold Year" />
              <SortableHeader field="is_partner_sale" label="Partner Sale" />
              <SortableHeader field="semrush_a_score" label="SEMrush A Score" />
              <SortableHeader field="ahrefs_backlinks" label="Ahrefs Backlinks" />
              <SortableHeader field="semrush_backlinks" label="SEMrush Backlinks" />
              <SortableHeader field="majestic_trust_flow" label="Majestic TF" />
              <SortableHeader field="go_value" label="GO Value" />
              <SortableHeader field="bid_count" label="Bids" />
            </TableRow>
          </TableHead>
          <TableBody>
            {domains.map((domain) => (
              <TableRow
                key={domain.id}
                hover
                onClick={() => handleSelectRow(domain.id)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selectedDomains.has(domain.id)}
                    onChange={() => handleSelectRow(domain.id)}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {domain.name}
                  </Typography>
                </TableCell>
                <TableCell>
                  {domain.total_meaning_score !== undefined ? (
                    <Typography variant="body2" fontWeight="medium" color="primary">
                      {domain.total_meaning_score.toFixed(2)}
                    </Typography>
                  ) : (
                    '-'
                  )}
                </TableCell>
                <TableCell>
                  {domain.rank !== undefined ? (
                    <Typography variant="body2">
                      #{domain.rank}
                    </Typography>
                  ) : (
                    '-'
                  )}
                </TableCell>
                <TableCell>
                  {domain.filter_status ? (
                    <Chip
                      label={domain.filter_status}
                      color={domain.filter_status === 'PASS' ? 'success' : 'error'}
                      size="small"
                      title={domain.filter_reason || undefined}
                    />
                  ) : (
                    '-'
                  )}
                </TableCell>
                <TableCell>{formatCurrency(domain.price)}</TableCell>
                <TableCell>{formatDate(domain.end_date)}</TableCell>
                <TableCell>{formatNumber(domain.ahrefs_domain_rating)}</TableCell>
                <TableCell>{formatCurrency(domain.estibot_value)}</TableCell>
                <TableCell>{formatNumber(domain.keyword_search_count)}</TableCell>
                <TableCell>{formatNumber(domain.last_sold_year)}</TableCell>
                <TableCell>{formatBoolean(domain.is_partner_sale)}</TableCell>
                <TableCell>{formatNumber(domain.semrush_a_score)}</TableCell>
                <TableCell>{formatNumber(domain.ahrefs_backlinks)}</TableCell>
                <TableCell>{formatNumber(domain.semrush_backlinks)}</TableCell>
                <TableCell>{formatNumber(domain.majestic_trust_flow)}</TableCell>
                <TableCell>{formatCurrency(domain.go_value)}</TableCell>
                <TableCell>{formatNumber(domain.bid_count)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      )}
    </Box>
  );
};

export default NamecheapDomainTable;
