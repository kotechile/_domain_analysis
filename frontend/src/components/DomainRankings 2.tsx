import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  LinearProgress,
  Alert,
  Button,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  NewReleases as NewReleasesIcon,
  Remove as RemoveIcon,
  Search as SearchIcon,
  Paid as PaidIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';

import { DataForSEOMetrics, OrganicMetrics, PaidMetrics } from '../services/api';

interface DomainRankingsProps {
  metrics?: DataForSEOMetrics;
  domain?: string;
}

const DomainRankings: React.FC<DomainRankingsProps> = ({ metrics, domain }) => {
  if (!metrics) {
    return (
      <Alert severity="info">
        No domain ranking data available for this domain.
      </Alert>
    );
  }

  const organic = metrics.organic_metrics;
  const paid = metrics.paid_metrics;

  const formatNumber = (num: number | undefined | null) => {
    if (num === undefined || num === null) return 'N/A';
    return num.toLocaleString();
  };

  const formatCurrency = (num: number | undefined | null) => {
    if (num === undefined || num === null) return 'N/A';
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  const getPositionDistribution = (metrics: OrganicMetrics | PaidMetrics | undefined) => {
    if (!metrics) return [];
    
    return [
      { range: '1', count: metrics.pos_1, color: '#4caf50' },
      { range: '2-3', count: metrics.pos_2_3, color: '#8bc34a' },
      { range: '4-10', count: metrics.pos_4_10, color: '#ffc107' },
      { range: '11-20', count: metrics.pos_11_20, color: '#ff9800' },
      { range: '21-30', count: metrics.pos_21_30, color: '#ff5722' },
      { range: '31-40', count: metrics.pos_31_40, color: '#f44336' },
      { range: '41-50', count: metrics.pos_41_50, color: '#e91e63' },
      { range: '51-60', count: metrics.pos_51_60, color: '#9c27b0' },
      { range: '61-70', count: metrics.pos_61_70, color: '#673ab7' },
      { range: '71-80', count: metrics.pos_71_80, color: '#3f51b5' },
      { range: '81-90', count: metrics.pos_81_90, color: '#2196f3' },
      { range: '91-100', count: metrics.pos_91_100, color: '#03a9f4' },
    ];
  };

  const getKeywordTrends = (metrics: OrganicMetrics | PaidMetrics | undefined) => {
    if (!metrics) return [];
    
    return [
      { label: 'New Keywords', count: metrics.is_new, icon: <NewReleasesIcon />, color: 'success' },
      { label: 'Keywords Moved Up', count: metrics.is_up, icon: <TrendingUpIcon />, color: 'success' },
      { label: 'Keywords Moved Down', count: metrics.is_down, icon: <TrendingDownIcon />, color: 'warning' },
      { label: 'Lost Keywords', count: metrics.is_lost, icon: <RemoveIcon />, color: 'error' },
    ];
  };

  const organicDistribution = getPositionDistribution(organic);
  const paidDistribution = getPositionDistribution(paid);
  const organicTrends = getKeywordTrends(organic);
  const paidTrends = getKeywordTrends(paid);

  const maxOrganicCount = Math.max(...organicDistribution.map(d => d.count));
  const maxPaidCount = Math.max(...paidDistribution.map(d => d.count));

  if (!organic && !paid) {
    return (
      <Alert severity="info">
        No domain ranking data available for this domain.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Domain Rankings Analysis
      </Typography>

      <Grid container spacing={3}>
        {/* Organic Search Rankings */}
        {organic && (
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <SearchIcon color="primary" />
                  <Typography variant="h6">Organic Search Rankings</Typography>
                </Box>
                
                {/* Key Metrics */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Total Keywords</Typography>
                    <Typography variant="h6">{formatNumber(organic.count)}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Estimated Traffic Value</Typography>
                    <Typography variant="h6">{formatCurrency(organic.etv)}</Typography>
                  </Grid>
                </Grid>

                {/* Position Distribution */}
                <Typography variant="subtitle2" gutterBottom>
                  Position Distribution
                </Typography>
                <Box sx={{ mb: 3 }}>
                  {organicDistribution.map((item) => (
                    <Box key={item.range} sx={{ mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2">Position {item.range}</Typography>
                        <Typography variant="body2">{formatNumber(item.count)}</Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={maxOrganicCount > 0 ? (item.count / maxOrganicCount) * 100 : 0}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          backgroundColor: 'rgba(0,0,0,0.1)',
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: item.color,
                          },
                        }}
                      />
                    </Box>
                  ))}
                </Box>

                {/* Keyword Trends */}
                <Typography variant="subtitle2" gutterBottom>
                  Keyword Movement Trends
                </Typography>
                <Grid container spacing={1}>
                  {organicTrends.map((trend) => (
                    <Grid item xs={6} key={trend.label}>
                      <Chip
                        icon={trend.icon}
                        label={`${trend.label}: ${formatNumber(trend.count)}`}
                        color={trend.color as any}
                        variant="outlined"
                        size="small"
                        sx={{ width: '100%', justifyContent: 'flex-start' }}
                      />
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Paid Search Rankings */}
        {paid && (
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <PaidIcon color="secondary" />
                  <Typography variant="h6">Paid Search Rankings</Typography>
                </Box>
                
                {/* Key Metrics */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Total Keywords</Typography>
                    <Typography variant="h6">{formatNumber(paid.count)}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Estimated Traffic Value</Typography>
                    <Typography variant="h6">{formatCurrency(paid.etv)}</Typography>
                  </Grid>
                </Grid>

                {/* Position Distribution */}
                <Typography variant="subtitle2" gutterBottom>
                  Position Distribution
                </Typography>
                <Box sx={{ mb: 3 }}>
                  {paidDistribution.map((item) => (
                    <Box key={item.range} sx={{ mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2">Position {item.range}</Typography>
                        <Typography variant="body2">{formatNumber(item.count)}</Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={maxPaidCount > 0 ? (item.count / maxPaidCount) * 100 : 0}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          backgroundColor: 'rgba(0,0,0,0.1)',
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: item.color,
                          },
                        }}
                      />
                    </Box>
                  ))}
                </Box>

                {/* Keyword Trends */}
                <Typography variant="subtitle2" gutterBottom>
                  Keyword Movement Trends
                </Typography>
                <Grid container spacing={1}>
                  {paidTrends.map((trend) => (
                    <Grid item xs={6} key={trend.label}>
                      <Chip
                        icon={trend.icon}
                        label={`${trend.label}: ${formatNumber(trend.count)}`}
                        color={trend.color as any}
                        variant="outlined"
                        size="small"
                        sx={{ width: '100%', justifyContent: 'flex-start' }}
                      />
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Summary Table */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Ranking Summary
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Metric</TableCell>
                      <TableCell align="right">Organic</TableCell>
                      <TableCell align="right">Paid</TableCell>
                      <TableCell align="right">Total</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Total Keywords</TableCell>
                      <TableCell align="right">{formatNumber(organic?.count)}</TableCell>
                      <TableCell align="right">{formatNumber(paid?.count)}</TableCell>
                      <TableCell align="right">
                        {formatNumber((organic?.count || 0) + (paid?.count || 0))}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Estimated Traffic Value</TableCell>
                      <TableCell align="right">{formatCurrency(organic?.etv)}</TableCell>
                      <TableCell align="right">{formatCurrency(paid?.etv)}</TableCell>
                      <TableCell align="right">
                        {formatCurrency((organic?.etv || 0) + (paid?.etv || 0))}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Top 3 Positions</TableCell>
                      <TableCell align="right">
                        {formatNumber((organic?.pos_1 || 0) + (organic?.pos_2_3 || 0))}
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber((paid?.pos_1 || 0) + (paid?.pos_2_3 || 0))}
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber(
                          (organic?.pos_1 || 0) + (organic?.pos_2_3 || 0) + 
                          (paid?.pos_1 || 0) + (paid?.pos_2_3 || 0)
                        )}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Top 10 Positions</TableCell>
                      <TableCell align="right">
                        {formatNumber(
                          (organic?.pos_1 || 0) + (organic?.pos_2_3 || 0) + (organic?.pos_4_10 || 0)
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber(
                          (paid?.pos_1 || 0) + (paid?.pos_2_3 || 0) + (paid?.pos_4_10 || 0)
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber(
                          (organic?.pos_1 || 0) + (organic?.pos_2_3 || 0) + (organic?.pos_4_10 || 0) +
                          (paid?.pos_1 || 0) + (paid?.pos_2_3 || 0) + (paid?.pos_4_10 || 0)
                        )}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Wayback Machine Button */}
        {domain && (
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  Historical Analysis
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Explore this domain's historical performance and changes over time
                </Typography>
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<OpenInNewIcon />}
                  onClick={() => window.open(`https://web.archive.org/web/*/${domain}`, '_blank')}
                  sx={{ minWidth: 250 }}
                >
                  View on Wayback Machine
                </Button>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default DomainRankings;
