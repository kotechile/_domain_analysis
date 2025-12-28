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
  Chip,
  CircularProgress,
  Alert,
  Link,
  Tooltip,
  Button,
} from '@mui/material';
import {
  Link as LinkIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  OpenInNew as OpenInNewIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

import { useApi } from '../services/api';
import { formatDate } from '../utils/dateUtils';
import { exportBacklinksToCSV, BacklinkExportData } from '../utils/csvExport';

interface BacklinksTableProps {
  domain: string;
  reportData?: {
    data_for_seo_metrics?: {
      total_backlinks?: number;
      total_referring_domains?: number;
    };
    detailed_data_available?: {
      backlinks?: boolean;
      keywords?: boolean;
      referring_domains?: boolean;
    };
  };
  qualityMetrics?: {
    overall_quality_score: number;
    high_dr_percentage: number;
    link_diversity_score: number;
    relevance_score: number;
    velocity_score: number;
    geographic_diversity: number;
    anchor_text_diversity: number;
  };
}

const BacklinksTable: React.FC<BacklinksTableProps> = ({ domain, reportData, qualityMetrics }) => {
  const api = useApi();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [isExporting, setIsExporting] = useState(false);
  // Detailed data is now loaded automatically during analysis

  const {
    data: backlinksData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['backlinks', domain, page * rowsPerPage, rowsPerPage],
    queryFn: () => api.getBacklinks(domain, rowsPerPage, page * rowsPerPage),
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
      const exportData = await api.exportBacklinks(domain);
      
      if (!exportData || !exportData.backlinks || exportData.backlinks.length === 0) {
        alert('No backlinks data available for export');
        return;
      }
      
      // Convert to export format
      const backlinksForExport: BacklinkExportData[] = exportData.backlinks.map(backlink => ({
        domain: backlink.domain,
        domain_rank: backlink.domain_rank,
        anchor_text: backlink.anchor_text,
        backlinks_count: backlink.backlinks_count,
        first_seen: backlink.first_seen,
        last_seen: backlink.last_seen,
        // Additional comprehensive fields
        url_from: backlink.url_from || "",
        url_to: backlink.url_to || "",
        link_type: backlink.link_type || "",
        link_attributes: backlink.link_attributes || "",
        page_from_title: backlink.page_from_title || "",
        page_from_rank: backlink.page_from_rank || 0,
        page_from_internal_links_count: backlink.page_from_internal_links_count || 0,
        page_from_external_links_count: backlink.page_from_external_links_count || 0,
        page_from_rank_absolute: backlink.page_from_rank_absolute || 0,
        // Additional useful fields
        dofollow: backlink.dofollow || false,
        is_new: backlink.is_new || false,
        is_lost: backlink.is_lost || false,
        is_broken: backlink.is_broken || false,
        url_from_https: backlink.url_from_https || false,
        url_to_https: backlink.url_to_https || false,
        page_from_status_code: backlink.page_from_status_code || 0,
        url_to_status_code: backlink.url_to_status_code || 0,
        backlink_spam_score: backlink.backlink_spam_score || 0,
        url_to_spam_score: backlink.url_to_spam_score || 0,
        page_from_size: backlink.page_from_size || 0,
        page_from_encoding: backlink.page_from_encoding || "",
        page_from_language: backlink.page_from_language || "",
        domain_from_ip: backlink.domain_from_ip || "",
        domain_from_country: backlink.domain_from_country || "",
        domain_from_platform_type: backlink.domain_from_platform_type || [],
        semantic_location: backlink.semantic_location || "",
        alt: backlink.alt || "",
        image_url: backlink.image_url || "",
        text_pre: backlink.text_pre || "",
        text_post: backlink.text_post || "",
        tld_from: backlink.tld_from || "",
        domain_to: backlink.domain_to || "",
        is_indirect_link: backlink.is_indirect_link || false,
        indirect_link_path: backlink.indirect_link_path || "",
        url_to_redirect_target: backlink.url_to_redirect_target || "",
        prev_seen: backlink.prev_seen || "",
        group_count: backlink.group_count || 0,
        original: backlink.original || false,
        item_type: backlink.item_type || "",
        domain_from_is_ip: backlink.domain_from_is_ip || false
      }));
      
      exportBacklinksToCSV(backlinksForExport, domain);
    } catch (error) {
      console.error('Failed to export backlinks:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`Failed to export backlinks: ${errorMessage}`);
    } finally {
      setIsExporting(false);
    }
  };

  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null) return 'N/A';
    return num.toLocaleString();
  };

  const isUrl = (text: string): boolean => {
    try {
      new URL(text);
      return true;
    } catch {
      return false;
    }
  };

  const renderAnchorText = (anchorText: string | null) => {
    if (!anchorText) return 'N/A';
    
    if (isUrl(anchorText)) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <LinkIcon color="primary" fontSize="small" />
          <Link
            href={anchorText}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ 
              color: 'primary.main',
              textDecoration: 'none',
              '&:hover': {
                textDecoration: 'underline'
              }
            }}
          >
            {anchorText}
          </Link>
        </Box>
      );
    }
    
    return (
      <Typography variant="body2" color="text.primary">
        {anchorText}
      </Typography>
    );
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

  // Get backlinks from the paginated response
  // Note: Filtering is disabled because we're using server-side pagination
  const filteredBacklinks = backlinksData?.backlinks || [];



  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
        <CircularProgress />
        <Typography variant="body2" sx={{ ml: 2 }}>
          Loading detailed backlinks data...
        </Typography>
      </Box>
    );
  }

  if (error) {
    // Check if it's a 404 error (no data available) vs other errors
    if (error.message?.includes('404') || error.message?.includes('not found')) {
      return (
        <Alert severity="info">
          No detailed backlinks data available for this domain. The analysis may not have collected detailed backlinks data.
        </Alert>
      );
    }
    
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Showing {filteredBacklinks.length} of {formatNumber(backlinksData.total_count)} backlinks
          </Typography>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExportCSV}
            disabled={isExporting || !backlinksData?.backlinks?.length}
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
              <TableCell>Referring Domain</TableCell>
              <TableCell align="center">Domain Rank</TableCell>
              <TableCell align="center">Quality</TableCell>
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
                      {backlink.domain || 'N/A'}
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
                <TableCell align="center">
                  <Tooltip title={`Quality Score: ${Math.round((backlink.domain_rank || 0) / 10)}/10`} arrow>
                    <Chip
                      label={Math.round((backlink.domain_rank || 0) / 10)}
                      color={backlink.domain_rank >= 70 ? 'success' : 
                             backlink.domain_rank >= 40 ? 'warning' : 'error'}
                      size="small"
                      variant="filled"
                    />
                  </Tooltip>
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
                  <Tooltip 
                    title={
                      backlink.anchor_text 
                        ? (isUrl(backlink.anchor_text) 
                            ? `Clickable URL: ${backlink.anchor_text}` 
                            : `Anchor text: ${backlink.anchor_text}`)
                        : 'No anchor text available'
                    } 
                    arrow
                  >
                    <Box
                      sx={{
                        maxWidth: 200,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {renderAnchorText(backlink.anchor_text)}
                    </Box>
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
                      href={`https://${backlink.domain || 'example.com'}`}
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
