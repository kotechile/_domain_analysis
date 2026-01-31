import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Box,
  Typography,
  Link,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { BulkPageSummaryResult, NamecheapDomain, NamecheapAnalysisResult } from '../services/api';

interface NamecheapAnalysisResultsProps {
  results: NamecheapAnalysisResult[];
  namecheapDomains: NamecheapDomain[];
}

const NamecheapAnalysisResults: React.FC<NamecheapAnalysisResultsProps> = ({
  results,
  namecheapDomains,
}) => {
  // Create a map for quick lookup of Namecheap data
  const namecheapMap = new Map(namecheapDomains.map(d => [d.name, d]));

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

  const getStatusChip = (result: NamecheapAnalysisResult) => {
    switch (result.status) {
      case 'has_data':
        return <Chip label="Complete" color="success" size="small" icon={<CheckCircleIcon />} />;
      case 'triggered':
        return <Chip label="Pending" color="warning" size="small" icon={<ScheduleIcon />} />;
      case 'error':
        return <Chip label="Error" color="error" size="small" icon={<ErrorIcon />} />;
      default:
        return <Chip label="Pending" color="default" size="small" />;
    }
  };

  const getSpamScoreColor = (score?: number): 'default' | 'warning' | 'error' => {
    if (score === undefined || score === null) return 'default';
    if (score > 30) return 'error';
    if (score > 20) return 'warning';
    return 'default';
  };

  if (results.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No analysis results to display. Select domains and click "Analyze in Bulk" to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Domain</TableCell>
            <TableCell>Namecheap Price</TableCell>
            <TableCell>End Date</TableCell>
            <TableCell>DataForSeo Rank</TableCell>
            <TableCell>Backlinks</TableCell>
            <TableCell>Referring Domains</TableCell>
            <TableCell>Spam Score</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {results.map((result) => {
            const namecheapData = namecheapMap.get(result.domain) || result.namecheap_data;
            const dataforseo = result.dataforseo_data;
            const hasHighSpam = (dataforseo?.backlinks_spam_score ?? 0) > 30;

            return (
              <TableRow
                key={result.domain}
                sx={{
                  backgroundColor: hasHighSpam ? 'rgba(244, 67, 54, 0.05)' : undefined,
                  '&:hover': {
                    backgroundColor: hasHighSpam ? 'rgba(244, 67, 54, 0.1)' : undefined,
                  },
                }}
              >
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {result.domain}
                  </Typography>
                  {namecheapData?.url && (
                    <Link
                      href={namecheapData.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ fontSize: '0.75rem' }}
                    >
                      View on Namecheap
                    </Link>
                  )}
                </TableCell>
                <TableCell>{formatCurrency(namecheapData?.price)}</TableCell>
                <TableCell>{formatDate(namecheapData?.end_date)}</TableCell>
                <TableCell>{formatNumber(dataforseo?.rank)}</TableCell>
                <TableCell>{formatNumber(dataforseo?.backlinks)}</TableCell>
                <TableCell>{formatNumber(dataforseo?.referring_domains)}</TableCell>
                <TableCell>
                  {dataforseo?.backlinks_spam_score !== undefined ? (
                    <Chip
                      label={formatNumber(dataforseo.backlinks_spam_score)}
                      color={getSpamScoreColor(dataforseo.backlinks_spam_score)}
                      size="small"
                    />
                  ) : (
                    '-'
                  )}
                </TableCell>
                <TableCell>{getStatusChip(result)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default NamecheapAnalysisResults;
