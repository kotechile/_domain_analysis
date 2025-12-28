import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Button,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Stack,
  useTheme,
  Radio,
  RadioGroup,
  FormControlLabel,
} from '@mui/material';
import {
  FilterList as FilterListIcon,
  CloudUpload as CloudUploadIcon,
  MoreVert as MoreVertIcon,
  InsertDriveFile as InsertDriveFileIcon,
  TrendingUp as TrendingUpIcon,
  FiberNew as FiberNewIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

import { useApi } from '../services/api';
import Header from '../components/Header';
import DataForSEOPopup from '../components/DataForSEOPopup';
import LoadFilePopup from '../components/LoadFilePopup';
import FilterPopup, { FilterValues } from '../components/FilterPopup';

// Component for Analyze button that checks if domain has analysis
const DomainAnalyzeButton: React.FC<{
  domain: string;
  hasAnalysis: boolean;
  onCheckAnalysis: (domain: string, hasAnalysis: boolean) => void;
  onClick: (domain: string) => void;
}> = ({ domain, hasAnalysis, onCheckAnalysis, onClick }) => {
  const api = useApi();

  // Check if domain has analysis (only check once)
  useQuery({
    queryKey: ['domain-analysis-check', domain],
    queryFn: async () => {
      try {
        const report = await api.getReport(domain);
        const hasReport = report.success && report.report !== undefined;
        onCheckAnalysis(domain, hasReport);
        return hasReport;
      } catch (error) {
        // 404 means no analysis, which is fine
        onCheckAnalysis(domain, false);
        return false;
      }
    },
    enabled: !hasAnalysis, // Only check if we don't already know
    retry: false,
  });

  const buttonColor = hasAnalysis ? '#4CAF50' : '#66CCFF';
  const borderColor = hasAnalysis ? 'rgba(76, 175, 80, 0.3)' : 'rgba(102, 204, 255, 0.3)';
  const hoverBgColor = hasAnalysis ? 'rgba(76, 175, 80, 0.1)' : 'rgba(102, 204, 255, 0.1)';

  return (
    <Button
      variant="outlined"
      size="small"
      startIcon={<TrendingUpIcon />}
      onClick={() => onClick(domain)}
      sx={{
        color: buttonColor,
        borderColor: borderColor,
        textTransform: 'none',
        fontWeight: 500,
        '&:hover': {
          borderColor: buttonColor,
          backgroundColor: hoverBgColor,
        },
      }}
    >
      {hasAnalysis ? 'View Analysis' : 'Analyze'}
    </Button>
  );
};

// Helper function to get default date range (Now to Now+7 days)
// Expanded from 2 days to 7 days to show more domains across different TLDs
const getDefaultDateRange = () => {
  const now = new Date();
  const sevenDaysLater = new Date(now);
  sevenDaysLater.setDate(sevenDaysLater.getDate() + 7);
  
  return {
    from: now.toISOString().split('T')[0],
    to: sevenDaysLater.toISOString().split('T')[0],
  };
};

const DomainsTablePage: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const api = useApi();
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [popupOpen, setPopupOpen] = useState(false);
  const [loadFilePopupOpen, setLoadFilePopupOpen] = useState(false);
  const [filterPopupOpen, setFilterPopupOpen] = useState(false);
  const [waybackLoading, setWaybackLoading] = useState<Set<string>>(new Set());
  const [queueStatuses, setQueueStatuses] = useState<Map<string, { position?: number; queue_count?: number; domain_queued?: boolean }>>(new Map());
  const [queueingDomains, setQueueingDomains] = useState<Set<string>>(new Set());
  const [domainsWithAnalysis, setDomainsWithAnalysis] = useState<Set<string>>(new Set());
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
    sortBy?: string;
    sortOrder?: string;
  }>({});

  // Load filter settings on mount
  const { data: filterData, isLoading: isLoadingFilters } = useQuery({
    queryKey: ['filters'],
    queryFn: () => api.getFilters(),
  });

  // Track if filters have been manually set by user
  const [filtersManuallySet, setFiltersManuallySet] = useState(false);

  // Apply filter settings when data loads (only if not manually set)
  useEffect(() => {
    if (!filtersManuallySet && filterData?.success && filterData?.filter) {
      setFilters({
        preferred: filterData.filter.preferred ?? undefined,
        auctionSite: filterData.filter.auction_site ?? undefined,
        tld: filterData.filter.tld ?? undefined,
        tlds: filterData.filter.tlds ?? undefined,
        hasStatistics: filterData.filter.has_statistics ?? undefined,
        scored: filterData.filter.scored ?? undefined,
        minRank: filterData.filter.min_rank ?? undefined,
        maxRank: filterData.filter.max_rank ?? undefined,
        minScore: filterData.filter.min_score ?? undefined,
        maxScore: filterData.filter.max_score ?? undefined,
        expirationFromDate: filterData.filter.expiration_from_date ?? undefined,
        expirationToDate: filterData.filter.expiration_to_date ?? undefined,
        sortBy: filterData.filter.sort_by || 'expiration_date',
        sortOrder: filterData.filter.sort_order || 'asc',
      });
      setRowsPerPage(filterData.filter.page_size || 50);
    }
  }, [filterData, filtersManuallySet]);

  // Load auctions data
  const {
    data: auctionsData,
    isLoading: isLoadingAuctions,
    error: auctionsError,
    refetch: refetchAuctions,
  } = useQuery({
    queryKey: ['auctions-report', filters, page, rowsPerPage],
    queryFn: () => {
      // Apply default date range if no dates are selected
      const defaultDates = getDefaultDateRange();
      const expirationFromDate = filters.expirationFromDate || defaultDates.from;
      const expirationToDate = filters.expirationToDate || defaultDates.to;
      
      // Debug logging
      console.log('Fetching auctions with filters:', {
        tlds: filters.tlds,
        expirationFromDate,
        expirationToDate,
        otherFilters: {
          preferred: filters.preferred,
          auctionSite: filters.auctionSite,
          offeringType: filters.offeringType,
          scored: filters.scored,
        }
      });
      
      return api.getAuctionsReport(
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
        expirationFromDate,
        expirationToDate,
        filters.sortBy || 'expiration_date',
        filters.sortOrder || 'asc',
        rowsPerPage,
        page * rowsPerPage
      );
    },
    enabled: !isLoadingFilters, // Wait for filters to load
    refetchInterval: 60000, // Refetch every 60 seconds to catch n8n webhook updates
  });

  // Debug logging for auctions data
  useEffect(() => {
    if (auctionsData) {
      console.log('Auctions query success:', {
        count: auctionsData?.count,
        total_count: auctionsData?.total_count,
        auctions_length: auctionsData?.auctions?.length,
        filters_applied: filters,
      });
    }
  }, [auctionsData, filters]);

  useEffect(() => {
    if (auctionsError) {
      console.error('Auctions query error:', auctionsError);
    }
  }, [auctionsError]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleMoreClick = async (domain: string) => {
    // Check if domain already has an analysis
    try {
      const report = await api.getReport(domain);
      if (report.success && report.report) {
        // Domain has analysis, navigate to the report page
        navigate(`/reports/${domain}`);
      } else {
        // No analysis exists, navigate to main page with domain pre-filled
        navigate(`/?domain=${encodeURIComponent(domain)}`);
      }
    } catch (error) {
      // If error (likely 404), navigate to main page with domain pre-filled
      navigate(`/?domain=${encodeURIComponent(domain)}`);
    }
  };

  const handleQueueRequest = async (domain: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    const queueStatus = queueStatuses.get(domain);
    
    // If already queued, cancel it
    if (queueStatus?.domain_queued) {
      setQueueingDomains(prev => new Set(prev).add(domain));
      
      try {
        const result = await api.cancelDomainQueueRequest(domain);
        
        if (result.success && result.cancelled) {
          // Remove from queue status
          setQueueStatuses(prev => {
            const newMap = new Map(prev);
            newMap.delete(domain);
            return newMap;
          });
        }
      } catch (error: any) {
        console.error('Failed to cancel queue request:', error);
      } finally {
        setQueueingDomains(prev => {
          const newSet = new Set(prev);
          newSet.delete(domain);
          return newSet;
        });
      }
      return;
    }
    
    // Otherwise, add to queue
    setQueueingDomains(prev => new Set(prev).add(domain));
    
    try {
      const result = await api.queueDomainForDataForSEO(domain);
      
      if (result.success && result.queued) {
        // Update queue status for this domain
        setQueueStatuses(prev => {
          const newMap = new Map(prev);
          newMap.set(domain, {
            position: result.position,
            queue_count: result.queue_count,
            domain_queued: true,
          });
          return newMap;
        });
      }
    } catch (error: any) {
      console.error('Failed to queue domain:', error);
    } finally {
      setQueueingDomains(prev => {
        const newSet = new Set(prev);
        newSet.delete(domain);
        return newSet;
      });
    }
  };

  // Fetch queue status for domains without page_statistics
  useEffect(() => {
    if (!auctionsData?.auctions) return;
    
    const domainsWithoutStats = auctionsData.auctions
      .filter(auction => !auction.page_statistics && !auction.statistics)
      .map(auction => auction.domain);
    
    if (domainsWithoutStats.length === 0) return;
    
    const fetchQueueStatuses = async () => {
      // Batch requests to avoid overwhelming the backend
      // Process in chunks of 10 domains at a time with a small delay between chunks
      const BATCH_SIZE = 10;
      const BATCH_DELAY = 100; // 100ms delay between batches
      
      const newStatuses = new Map<string, { position?: number; queue_count?: number; domain_queued?: boolean }>();
      
      for (let i = 0; i < domainsWithoutStats.length; i += BATCH_SIZE) {
        const batch = domainsWithoutStats.slice(i, i + BATCH_SIZE);
        
        const statusPromises = batch.map(async (domain) => {
          try {
            const status = await api.getDataForSEOQueueStatus(domain);
            return { domain, status };
          } catch (error) {
            // Silently handle errors to avoid console spam
            return { domain, status: null };
          }
        });
        
        const results = await Promise.all(statusPromises);
        
        results.forEach(({ domain, status }) => {
          if (status) {
            newStatuses.set(domain, {
              position: status.position,
              queue_count: status.queue_count,
              domain_queued: status.domain_queued,
            });
          }
        });
        
        // Add delay between batches to avoid overwhelming the backend
        if (i + BATCH_SIZE < domainsWithoutStats.length) {
          await new Promise(resolve => setTimeout(resolve, BATCH_DELAY));
        }
      }
      
      setQueueStatuses(prev => {
        const merged = new Map(prev);
        newStatuses.forEach((value, key) => merged.set(key, value));
        return merged;
      });
    };
    
    fetchQueueStatuses();
    
    // Poll every 30 seconds (increased from 10 to reduce load)
    const interval = setInterval(fetchQueueStatuses, 30000);
    return () => clearInterval(interval);
  }, [auctionsData?.auctions, api]);

  // Get provider auction URL based on auction_site
  const getProviderAuctionUrl = (domain: string, auctionSite?: string): string => {
    const site = (auctionSite || '').toLowerCase();
    
    if (site === 'namecheap') {
      return `https://www.namecheap.com/market/${domain}/`;
    } else if (site === 'godaddy' || site === 'go daddy') {
      return `https://auctions.godaddy.com/`;
    } else if (site === 'namesilo') {
      return `https://www.namesilo.com/marketplace`;
    } else if (site === 'catchclub' || site === 'catch.club') {
      return `https://catch.club/bid/${domain}`;
    }
    
    // Default fallback
    return `https://www.namecheap.com/market/${domain}/`;
  };

  // Handle clicking on domain name - open provider auction site
  const handleDomainClick = (domain: string, auctionSite?: string, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    const url = getProviderAuctionUrl(domain, auctionSite);
    window.open(url, '_blank');
  };

  // Handle clicking on First Seen - open Wayback Machine and check first seen date
  const handleFirstSeenClick = async (domain: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    // Open Wayback Machine URL immediately
    const waybackUrl = `https://web.archive.org/web/*/${domain}`;
    window.open(waybackUrl, '_blank');
    
    // If already loading, don't fetch again
    if (waybackLoading.has(domain)) {
      return;
    }
    
    // Fetch first seen date from API with timeout
    setWaybackLoading(prev => new Set(prev).add(domain));
    
    // Set a timeout to clear loading state if request takes too long
    const timeoutId = setTimeout(() => {
      setWaybackLoading(prev => {
        const newSet = new Set(prev);
        newSet.delete(domain);
        return newSet;
      });
    }, 20000); // 20 second fallback timeout
    
    try {
      const result = await api.fetchWaybackFirstSeen(domain);
      clearTimeout(timeoutId);
      
      if (result.success && result.first_seen) {
        // Refetch auctions to update the display with the new first_seen from database
        await refetchAuctions();
      } else {
        // Log the message if available (but don't show error to user since Wayback Machine opened)
        if (result.message) {
          console.warn('Wayback Machine search result:', result.message, 'for domain:', domain);
        }
      }
    } catch (error: any) {
      clearTimeout(timeoutId);
      
      // Check if it's a timeout error
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout') || error.response?.status === 408) {
        console.warn('Wayback Machine request timed out for domain:', domain);
      } else {
        console.error('Failed to fetch Wayback Machine first seen:', error);
      }
      
      // Note: We don't show an error to the user because the Wayback Machine page already opened
      // The loading state will be cleared, and they can try again if needed
    } finally {
      // Always ensure loading state is cleared, even if there was an error
      setWaybackLoading(prev => {
        const newSet = new Set(prev);
        newSet.delete(domain);
        return newSet;
      });
    }
  };

  const handleClosePopup = () => {
    setPopupOpen(false);
    setSelectedDomain(null);
  };

  const handleSetFilters = () => {
    setFilterPopupOpen(true);
  };

  const handleFilterApply = async (filterValues: FilterValues) => {
    // Mark filters as manually set to prevent auto-clearing
    setFiltersManuallySet(true);
    
    // Update local filters state
    const newFilters = {
      ...filters,
      tlds: filterValues.tlds, // This will be undefined if "All" is selected, or an array like ['.com'] if specific TLDs are selected
      expirationFromDate: filterValues.expirationFromDate,
      expirationToDate: filterValues.expirationToDate,
      scored: filterValues.scored,
      minScore: filterValues.minScore,
      maxScore: filterValues.maxScore,
      // offeringType is now controlled by radio buttons in the header, not from FilterPopup
    };
    
    // Debug logging
    console.log('Applying filters:', {
      tlds: newFilters.tlds,
      tldsLength: newFilters.tlds?.length,
      expirationFromDate: newFilters.expirationFromDate,
      expirationToDate: newFilters.expirationToDate,
    });
    
    setFilters(newFilters);

    // Save to backend
    try {
      await api.updateFilters({
        tlds: filterValues.tlds,
        expiration_from_date: filterValues.expirationFromDate,
        expiration_to_date: filterValues.expirationToDate,
        scored: filterValues.scored,
        min_score: filterValues.minScore,
        max_score: filterValues.maxScore,
        sort_by: filters.sortBy || 'expiration_date',
        sort_order: filters.sortOrder || 'asc',
        page_size: rowsPerPage,
        is_default: true,
      });
    } catch (error) {
      console.error('Failed to save filters:', error);
    }
  };

  const handleLoadFiles = () => {
    // Open the new Load File popup
    setLoadFilePopupOpen(true);
  };

  const handleSort = (field: string) => {
    const newSortBy = field;
    const newSortOrder = 
      filters.sortBy === field && filters.sortOrder === 'asc' ? 'desc' : 'asc';
    
    setFilters({
      ...filters,
      sortBy: newSortBy,
      sortOrder: newSortOrder,
    });
    setPage(0); // Reset to first page when sorting changes
  };

  const selectedAuction = auctionsData?.auctions?.find(
    (auction) => auction.domain === selectedDomain
  );

  // Get page_statistics from either page_statistics field or statistics field
  const pageStatistics = selectedAuction?.page_statistics || selectedAuction?.statistics || null;

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#0C152B' }}>
      <Header />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Header Section - Matching Screenshot */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box>
              <Typography
                variant="h3"
                component="h1"
                sx={{
                  color: '#FFFFFF',
                  fontWeight: 700,
                  fontSize: '2rem',
                  mb: 1,
                }}
              >
                Live Marketplace
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  color: 'rgba(255, 255, 255, 0.7)',
                  fontSize: '0.95rem',
                  mb: 2,
                }}
              >
                Exploring current auctions and expiring domains across all major registries.
              </Typography>
              {/* Offer Type Radio Buttons */}
              <RadioGroup
                row
                value={filters.offeringType || ''}
                onChange={(e) => {
                  const newOfferingType = e.target.value || undefined;
                  setFilters({
                    ...filters,
                    offeringType: newOfferingType,
                  });
                  setPage(0); // Reset to first page when filter changes
                }}
                sx={{
                  '& .MuiFormControlLabel-root': {
                    marginRight: 3,
                  },
                  '& .MuiRadio-root': {
                    color: 'rgba(255, 255, 255, 0.7)',
                    '&.Mui-checked': {
                      color: '#1976d2',
                    },
                  },
                  '& .MuiFormControlLabel-label': {
                    color: '#FFFFFF',
                    fontSize: '0.95rem',
                  },
                }}
              >
                <FormControlLabel value="" control={<Radio />} label="All" />
                <FormControlLabel value="auction" control={<Radio />} label="Auction" />
                <FormControlLabel value="buy_now" control={<Radio />} label="Buy Now" />
              </RadioGroup>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Chip
                icon={<FiberNewIcon sx={{ color: '#4CAF50 !important' }} />}
                label={`${auctionsData?.total_count || 0} NEW TODAY`}
                sx={{
                  bgcolor: 'rgba(76, 175, 80, 0.2)',
                  color: '#4CAF50',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  border: '1px solid rgba(76, 175, 80, 0.3)',
                  '& .MuiChip-icon': {
                    color: '#4CAF50',
                  },
                }}
              />
              <IconButton
                onClick={handleLoadFiles}
                sx={{
                  color: '#FFFFFF',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                <InsertDriveFileIcon />
              </IconButton>
              <IconButton
                onClick={handleSetFilters}
                sx={{
                  color: '#FFFFFF',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                <FilterListIcon />
              </IconButton>
            </Box>
          </Box>
        </Box>

        {/* Table Section */}
        <Paper
          sx={{
            bgcolor: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '12px',
            overflow: 'hidden',
          }}
        >
          {isLoadingAuctions ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress sx={{ color: '#66CCFF' }} />
            </Box>
          ) : auctionsError ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography sx={{ color: '#FF5252' }}>
                Failed to load domains: {auctionsError instanceof Error ? auctionsError.message : 'Unknown error'}
              </Typography>
              <Button onClick={() => refetchAuctions()} sx={{ mt: 2, color: '#FFFFFF' }}>
                Retry
              </Button>
            </Box>
          ) : (
            <>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'rgba(255, 255, 255, 0.05)' }}>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        <TableSortLabel
                          active={filters.sortBy === 'domain'}
                          direction={filters.sortBy === 'domain' ? (filters.sortOrder as 'asc' | 'desc') : 'asc'}
                          onClick={() => handleSort('domain')}
                          sx={{
                            color: '#FFFFFF',
                            '& .MuiTableSortLabel-icon': {
                              color: '#FFFFFF !important',
                            },
                            '&:hover': {
                              color: '#66CCFF',
                            },
                          }}
                        >
                          Domain Name
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        Offer Type
                      </TableCell>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        <TableSortLabel
                          active={filters.sortBy === 'score'}
                          direction={filters.sortBy === 'score' ? (filters.sortOrder as 'asc' | 'desc') : 'desc'}
                          onClick={() => handleSort('score')}
                          sx={{
                            color: '#FFFFFF',
                            '& .MuiTableSortLabel-icon': {
                              color: '#FFFFFF !important',
                            },
                            '&:hover': {
                              color: '#66CCFF',
                            },
                          }}
                        >
                          Score
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        <TableSortLabel
                          active={filters.sortBy === 'current_bid'}
                          direction={filters.sortBy === 'current_bid' ? (filters.sortOrder as 'asc' | 'desc') : 'asc'}
                          onClick={() => handleSort('current_bid')}
                          sx={{
                            color: '#FFFFFF',
                            '& .MuiTableSortLabel-icon': {
                              color: '#FFFFFF !important',
                            },
                            '&:hover': {
                              color: '#66CCFF',
                            },
                          }}
                        >
                          Price
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        SEO Metrics (DR)
                      </TableCell>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        <TableSortLabel
                          active={filters.sortBy === 'expiration_date'}
                          direction={filters.sortBy === 'expiration_date' ? (filters.sortOrder as 'asc' | 'desc') : 'asc'}
                          onClick={() => handleSort('expiration_date')}
                          sx={{
                            color: '#FFFFFF',
                            '& .MuiTableSortLabel-icon': {
                              color: '#FFFFFF !important',
                            },
                            '&:hover': {
                              color: '#66CCFF',
                            },
                          }}
                        >
                          Expiry
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        <TableSortLabel
                          active={filters.sortBy === 'first_seen'}
                          direction={filters.sortBy === 'first_seen' ? (filters.sortOrder as 'asc' | 'desc') : 'asc'}
                          onClick={() => handleSort('first_seen')}
                          sx={{
                            color: '#FFFFFF',
                            '& .MuiTableSortLabel-icon': {
                              color: '#FFFFFF !important',
                            },
                            '&:hover': {
                              color: '#66CCFF',
                            },
                          }}
                        >
                          First Seen
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                        Action
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {auctionsData?.auctions?.map((auction) => {
                      // Extract SEO metrics from page_statistics and extracted columns
                      // Priority: extracted columns > page_statistics JSONB > statistics (legacy)
                      const pageStats = auction.page_statistics || auction.statistics || {};
                      
                      // Extract rank - check page_statistics first, then ranking column
                      const rank = (pageStats.rank !== undefined && pageStats.rank !== null) 
                        ? pageStats.rank 
                        : ((auction.ranking !== undefined && auction.ranking !== null) ? auction.ranking : null);
                      
                      // Extract backlinks - check extracted column first, then page_statistics
                      const backlinks = (auction.backlinks !== undefined && auction.backlinks !== null)
                        ? auction.backlinks
                        : ((pageStats.backlinks !== undefined && pageStats.backlinks !== null) ? pageStats.backlinks : null);
                      
                      // Extract spam score - check extracted column first, then page_statistics
                      // Also check for "spam_score" (DataForSEO format) as fallback
                      const spamScore = (auction.backlinks_spam_score !== undefined && auction.backlinks_spam_score !== null)
                        ? auction.backlinks_spam_score
                        : ((pageStats.backlinks_spam_score !== undefined && pageStats.backlinks_spam_score !== null) 
                          ? pageStats.backlinks_spam_score 
                          : ((pageStats as any).spam_score !== undefined && (pageStats as any).spam_score !== null) ? (pageStats as any).spam_score : null);
                      
                      // Extract referring domains - check extracted column first, then page_statistics
                      const referringDomains = (auction.referring_domains !== undefined && auction.referring_domains !== null)
                        ? auction.referring_domains
                        : ((pageStats.referring_domains !== undefined && pageStats.referring_domains !== null) ? pageStats.referring_domains : null);
                      
                      // Calculate DR from available data
                      // DR (Domain Rating) - convert rank from 0-1000 scale to 0-100 scale
                      const dr = rank !== null && rank !== undefined ? Math.round(rank / 10) : null; // Convert 0-1000 to 0-100
                      
                      // Format backlinks for display (e.g., 12400 -> "12.4k")
                      const formatBacklinks = (count: number | null): string => {
                        if (count === null || count === undefined) return '';
                        if (count >= 1000) {
                          return `${(count / 1000).toFixed(1)}k`;
                        }
                        return count.toString();
                      };
                      
                      // Format referring domains for display (e.g., 12400 -> "12.4k")
                      const formatReferringDomains = (count: number | null): string => {
                        if (count === null || count === undefined) return '';
                        if (count >= 1000) {
                          return `${(count / 1000).toFixed(1)}k`;
                        }
                        return count.toString();
                      };
                      
                      // Determine offer type from offer_type column
                      const getOfferType = (): { label: string; color: string } => {
                        // Use offer_type from the column (preferred) or fallback to source_data
                        const offerTypeValue = auction.offer_type || 
                                        (auction.source_data as any)?.offering_type || 
                                        (auction.source_data as any)?.offeringType || 
                                        (auction.source_data as any)?.Type || 
                                        null;
                        
                        // Normalize the offer type value to lowercase for comparison
                        const normalizedType = offerTypeValue ? offerTypeValue.toString().toLowerCase().trim() : null;
                        
                        // Map offer_type values to display labels and colors
                        if (normalizedType === 'buy_now' || normalizedType === 'buy-now') {
                          return { label: 'BUY NOW', color: '#2196F3' }; // Blue
                        }
                        
                        if (normalizedType === 'backorder') {
                          return { label: 'BACKORDER', color: '#9C27B0' }; // Purple
                        }
                        
                        if (normalizedType === 'auction') {
                          return { label: 'AUCTION', color: '#FF9800' }; // Orange
                        }
                        
                        // If we have a value but it doesn't match known types, show it as-is (capitalized)
                        if (normalizedType) {
                          const displayLabel = normalizedType.split('_').map((word: string) => 
                            word.charAt(0).toUpperCase() + word.slice(1)
                          ).join(' ').toUpperCase();
                          return { label: displayLabel, color: '#FF9800' }; // Default to orange
                        }
                        
                        // Check if expiring soon (within 7 days) - only if no offer_type is set
                        const expirationDate = auction.expiration_date ? new Date(auction.expiration_date) : null;
                        const daysUntilExpiry = expirationDate 
                          ? Math.ceil((expirationDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24))
                          : null;
                        
                        if (daysUntilExpiry !== null && daysUntilExpiry <= 7 && daysUntilExpiry >= 0) {
                          return { label: 'EXPIRING SOON', color: '#FF5252' }; // Red
                        }
                        
                        // Default to AUCTION if no type found
                        return { label: 'AUCTION', color: '#FF9800' }; // Orange
                      };
                      
                      const offerType = getOfferType();

                      return (
                        <TableRow
                          key={auction.id || auction.domain}
                          sx={{
                            '&:hover': {
                              bgcolor: 'rgba(255, 255, 255, 0.02)',
                            },
                          }}
                        >
                          {/* Domain Name - Clickable for Provider Auction Site */}
                          <TableCell sx={{ color: '#FFFFFF', fontWeight: 500 }}>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                                cursor: 'pointer',
                                '&:hover': {
                                  color: '#66CCFF',
                                },
                              }}
                              onClick={(e) => handleDomainClick(auction.domain, auction.auction_site, e)}
                            >
                              {auction.domain}
                            </Box>
                          </TableCell>
                          
                          {/* Offer Type */}
                          <TableCell>
                            <Chip
                              label={offerType.label}
                              size="small"
                              sx={{
                                bgcolor: offerType.color,
                                color: '#FFFFFF',
                                fontWeight: 600,
                                fontSize: '0.75rem',
                                height: '24px',
                                '& .MuiChip-label': {
                                  px: 1.5,
                                },
                              }}
                            />
                          </TableCell>
                          
                          {/* Score */}
                          <TableCell sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                            {auction.score !== null && auction.score !== undefined 
                              ? auction.score.toFixed(2)
                              : '—'}
                          </TableCell>
                          
                          {/* Price */}
                          <TableCell sx={{ color: '#4CAF50', fontWeight: 600 }}>
                            {auction.current_bid ? `$${auction.current_bid.toLocaleString()}` : '—'}
                          </TableCell>
                          
                          {/* SEO Metrics (DR, LINKS, Rank, Spam Score, Referring Domains) */}
                          <TableCell>
                            {(() => {
                              // Check if we have any data at all
                              const hasAnyData = dr !== null || backlinks !== null || rank !== null || spamScore !== null || referringDomains !== null;
                              
                              if (!hasAnyData) {
                                return <Box sx={{ minHeight: '40px' }} />; // Blank space when no data
                              }
                              
                              // Component for a single metric (label above value)
                              const MetricItem = ({ label, value }: { label: string; value: string | number | null }) => {
                                // Allow 0 as valid value, only exclude null/undefined
                                if (value === null || value === undefined || value === '') return null;
                                return (
                                  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', minWidth: '60px' }}>
                                    <Typography 
                                      sx={{ 
                                        color: 'rgba(255, 255, 255, 0.6)', 
                                        fontSize: '0.75rem', 
                                        fontWeight: 400,
                                        lineHeight: 1.2,
                                        mb: 0.25,
                                      }}
                                    >
                                      {label}
                                    </Typography>
                                    <Typography 
                                      sx={{ 
                                        color: '#FFFFFF', 
                                        fontWeight: 700, 
                                        fontSize: '1.1rem', 
                                        lineHeight: 1.2,
                                      }}
                                    >
                                      {value}
                                    </Typography>
                                  </Box>
                                );
                              };
                              
                              // Build array of metrics to display (only include those with data)
                              const metricsToShow = [];
                              
                              if (dr !== null && dr !== undefined) {
                                metricsToShow.push(<MetricItem key="dr" label="DR" value={dr} />);
                              }
                              if (backlinks !== null && backlinks !== undefined) {
                                metricsToShow.push(<MetricItem key="links" label="LINKS" value={formatBacklinks(backlinks)} />);
                              }
                              if (rank !== null && rank !== undefined) {
                                metricsToShow.push(<MetricItem key="rank" label="RANK" value={rank} />);
                              }
                              if (spamScore !== null && spamScore !== undefined) {
                                metricsToShow.push(<MetricItem key="spam" label="SPAM" value={spamScore} />);
                              }
                              if (referringDomains !== null && referringDomains !== undefined) {
                                metricsToShow.push(<MetricItem key="refdom" label="REF. DOM." value={formatReferringDomains(referringDomains)} />);
                              }
                              
                              return (
                                <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                                  {metricsToShow}
                                </Box>
                              );
                            })()}
                          </TableCell>
                          
                          {/* Expiry */}
                          <TableCell sx={{ color: '#FFFFFF' }}>
                            {auction.expiration_date
                              ? (() => {
                                  const date = new Date(auction.expiration_date);
                                  const year = date.getFullYear();
                                  const month = String(date.getMonth() + 1).padStart(2, '0');
                                  const day = String(date.getDate()).padStart(2, '0');
                                  const hours = String(date.getHours()).padStart(2, '0');
                                  const minutes = String(date.getMinutes()).padStart(2, '0');
                                  return `${month}-${day}-${year} ${hours}:${minutes}`;
                                })()
                              : 'N/A'}
                          </TableCell>
                          
                          {/* First Seen - Clickable for Wayback Machine */}
                          <TableCell>
                            <Button
                              variant="text"
                              size="small"
                              onClick={(e) => handleFirstSeenClick(auction.domain, e)}
                              disabled={waybackLoading.has(auction.domain)}
                              sx={{
                                color: auction.first_seen ? '#FFFFFF' : 'rgba(255, 255, 255, 0.5)',
                                textTransform: 'none',
                                fontWeight: 400,
                                minWidth: 'auto',
                                padding: '4px 8px',
                                '&:hover': {
                                  backgroundColor: 'rgba(102, 204, 255, 0.1)',
                                  color: '#66CCFF',
                                },
                                '&:disabled': {
                                  color: 'rgba(255, 255, 255, 0.3)',
                                },
                              }}
                              startIcon={
                                waybackLoading.has(auction.domain) ? (
                                  <CircularProgress size={14} sx={{ color: '#66CCFF' }} />
                                ) : (
                                  <HistoryIcon sx={{ fontSize: '1rem' }} />
                                )
                              }
                            >
                              {auction.first_seen
                                ? new Date(auction.first_seen).toLocaleDateString('en-US', {
                                    year: 'numeric',
                                    month: '2-digit',
                                    day: '2-digit',
                                  }).replace(/\//g, '-')
                                : '—'}
                            </Button>
                          </TableCell>
                          
                          {/* Action - Analyze Button */}
                          <TableCell>
                            <DomainAnalyzeButton 
                              domain={auction.domain}
                              hasAnalysis={domainsWithAnalysis.has(auction.domain)}
                              onCheckAnalysis={(domain, hasAnalysis) => {
                                if (hasAnalysis) {
                                  setDomainsWithAnalysis(prev => new Set(prev).add(domain));
                                }
                              }}
                              onClick={handleMoreClick}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    {(!auctionsData?.auctions || auctionsData.auctions.length === 0) && (
                      <TableRow>
                        <TableCell colSpan={8} align="center" sx={{ color: '#FFFFFF', py: 4 }}>
                          No domains found. Try adjusting your filters or load new files.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={auctionsData?.total_count || 0}
                page={page}
                onPageChange={handleChangePage}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                rowsPerPageOptions={[25, 50, 100]}
                sx={{
                  color: '#FFFFFF',
                  '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': {
                    color: '#FFFFFF',
                  },
                  '& .MuiIconButton-root': {
                    color: '#FFFFFF',
                  },
                }}
              />
            </>
          )}
        </Paper>

        {/* DataForSEO Popup */}
        {selectedDomain && (
          <DataForSEOPopup
            open={popupOpen}
            onClose={handleClosePopup}
            domain={selectedDomain}
            pageStatistics={pageStatistics}
          />
        )}

        {/* Load File Popup */}
        <LoadFilePopup
          open={loadFilePopupOpen}
          onClose={() => setLoadFilePopupOpen(false)}
        />

        {/* Filter Popup */}
        <FilterPopup
          open={filterPopupOpen}
          onClose={() => setFilterPopupOpen(false)}
          onApply={handleFilterApply}
          initialFilters={{
            tlds: filters.tlds,
            expirationFromDate: filters.expirationFromDate,
            expirationToDate: filters.expirationToDate,
            scored: filters.scored,
            minScore: filters.minScore,
            maxScore: filters.maxScore,
          }}
        />
      </Container>
    </Box>
  );
};

export default DomainsTablePage;


