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
  Chip,
  Box,
  Typography,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { BulkDomainAnalysis, BulkPageSummaryResult } from '../services/api';

interface BulkAnalysisTableProps {
  domains: BulkDomainAnalysis[];
  onSort?: (field: string, order: 'asc' | 'desc') => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

const BulkAnalysisTable: React.FC<BulkAnalysisTableProps> = ({
  domains,
  onSort,
  sortBy = 'created_at',
  sortOrder = 'desc',
}) => {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

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

  const getStatusChip = (summary?: BulkPageSummaryResult) => {
    if (!summary) {
      return <Chip label="Pending" color="warning" size="small" />;
    }
    return <Chip label="Complete" color="success" size="small" icon={<CheckCircleIcon />} />;
  };

  const getSpamScoreColor = (score?: number): 'default' | 'warning' | 'error' => {
    if (score === undefined || score === null) return 'default';
    if (score > 30) return 'error';
    if (score > 20) return 'warning';
    return 'default';
  };

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

  if (domains.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No bulk analysis data available. Upload a domain list to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <SortableHeader field="domain_name" label="Domain" />
            <TableCell>Provider</TableCell>
            <SortableHeader field="rank" label="Rank" />
            <SortableHeader field="backlinks" label="Backlinks" />
            <SortableHeader field="referring_domains" label="Referring Domains" />
            <SortableHeader field="referring_main_domains" label="Main Domains" />
            <TableCell>Spam Score</TableCell>
            <TableCell>Broken Backlinks</TableCell>
            <TableCell>First Seen</TableCell>
            <TableCell>Country</TableCell>
            <TableCell>CMS</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {domains.map((domain) => {
            const summary = domain.backlinks_bulk_page_summary;
            const hasHighSpam = (summary?.backlinks_spam_score ?? 0) > 30;
            const hasBrokenLinks = (summary?.broken_backlinks ?? 0) > 0;

            return (
              <React.Fragment key={domain.id}>
                <TableRow
                  hover
                  onClick={() => setExpandedRow(expandedRow === domain.id ? null : domain.id)}
                  sx={{
                    cursor: 'pointer',
                    backgroundColor: hasHighSpam ? 'rgba(244, 67, 54, 0.05)' : hasBrokenLinks ? 'rgba(33, 150, 243, 0.05)' : undefined,
                    '&:hover': {
                      backgroundColor: hasHighSpam ? 'rgba(244, 67, 54, 0.1)' : hasBrokenLinks ? 'rgba(33, 150, 243, 0.1)' : undefined,
                    },
                  }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {domain.domain_name}
                    </Typography>
                  </TableCell>
                  <TableCell>{domain.provider || '-'}</TableCell>
                  <TableCell>{formatNumber(summary?.rank)}</TableCell>
                  <TableCell>{formatNumber(summary?.backlinks)}</TableCell>
                  <TableCell>{formatNumber(summary?.referring_domains)}</TableCell>
                  <TableCell>{formatNumber(summary?.referring_main_domains)}</TableCell>
                  <TableCell>
                    <Chip
                      label={formatNumber(summary?.backlinks_spam_score)}
                      color={getSpamScoreColor(summary?.backlinks_spam_score)}
                      size="small"
                      icon={hasHighSpam ? <WarningIcon /> : undefined}
                    />
                  </TableCell>
                  <TableCell>
                    {hasBrokenLinks ? (
                      <Chip
                        label={formatNumber(summary?.broken_backlinks)}
                        color="info"
                        size="small"
                        icon={<InfoIcon />}
                      />
                    ) : (
                      formatNumber(summary?.broken_backlinks)
                    )}
                  </TableCell>
                  <TableCell>{formatDate(summary?.first_seen)}</TableCell>
                  <TableCell>{summary?.info?.country || '-'}</TableCell>
                  <TableCell>{summary?.info?.cms || '-'}</TableCell>
                  <TableCell>{getStatusChip(summary)}</TableCell>
                </TableRow>
                {expandedRow === domain.id && summary && (
                  <TableRow>
                    <TableCell colSpan={12} sx={{ backgroundColor: 'rgba(0, 0, 0, 0.02)' }}>
                      <Box sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>
                          Detailed Metrics for {domain.domain_name}
                        </Typography>
                        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mt: 2 }}>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Crawled Pages</Typography>
                            <Typography variant="body2">{formatNumber(summary.crawled_pages)}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Internal Links</Typography>
                            <Typography variant="body2">{formatNumber(summary.internal_links_count)}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">External Links</Typography>
                            <Typography variant="body2">{formatNumber(summary.external_links_count)}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Referring Pages</Typography>
                            <Typography variant="body2">{formatNumber(summary.referring_pages)}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Broken Pages</Typography>
                            <Typography variant="body2">{formatNumber(summary.broken_pages)}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Referring IPs</Typography>
                            <Typography variant="body2">{formatNumber(summary.referring_ips)}</Typography>
                          </Box>
                          {summary.info && (
                            <>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Server</Typography>
                                <Typography variant="body2">{summary.info.server || '-'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">IP Address</Typography>
                                <Typography variant="body2">{summary.info.ip_address || '-'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Target Spam Score</Typography>
                                <Typography variant="body2">{formatNumber(summary.info.target_spam_score)}</Typography>
                              </Box>
                            </>
                          )}
                        </Box>
                      </Box>
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default BulkAnalysisTable;
