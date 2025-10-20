import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Domain as DomainIcon,
  Link as LinkIcon,
  Search as SearchIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';

import { DomainAnalysisReport } from '../services/api';

interface ReportSummaryProps {
  report: DomainAnalysisReport;
}

const ReportSummary: React.FC<ReportSummaryProps> = ({ report }) => {
  const metrics = report.data_for_seo_metrics;
  const llmAnalysis = report.llm_analysis;
  const wayback = report.wayback_machine_summary;

  const formatNumber = (num: number | undefined) => {
    if (num === undefined) return 'N/A';
    return num.toLocaleString();
  };

  const formatPercentage = (num: number | undefined) => {
    if (num === undefined) return 'N/A';
    return `${(num * 100).toFixed(1)}%`;
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Analysis Summary
      </Typography>

      <Grid container spacing={3}>
        {/* Key Metrics */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Key SEO Metrics
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <DomainIcon color="primary" />
                    <Typography variant="body2">Domain Rating (DR)</Typography>
                  </Box>
                  <Typography variant="h6" color="primary">
                    {formatNumber(metrics?.domain_rating_dr)}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TrendingUpIcon color="success" />
                    <Typography variant="body2">Organic Traffic</Typography>
                  </Box>
                  <Typography variant="h6" color="success.main">
                    {formatNumber(metrics?.organic_traffic_est)}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinkIcon color="info" />
                    <Typography variant="body2">Referring Domains</Typography>
                  </Box>
                  <Typography variant="h6" color="info.main">
                    {formatNumber(metrics?.total_referring_domains)}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SearchIcon color="secondary" />
                    <Typography variant="body2">Total Backlinks</Typography>
                  </Box>
                  <Typography variant="h6" color="secondary.main">
                    {formatNumber(metrics?.total_backlinks)}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Historical Data */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Historical Data
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ScheduleIcon color="primary" />
                    <Typography variant="body2">Total Captures</Typography>
                  </Box>
                  <Typography variant="h6">
                    {formatNumber(wayback?.total_captures)}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ScheduleIcon color="primary" />
                    <Typography variant="body2">First Capture Year</Typography>
                  </Box>
                  <Typography variant="h6">
                    {wayback?.first_capture_year || 'N/A'}
                  </Typography>
                </Box>

                {wayback?.historical_risk_assessment && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    <Typography variant="body2">
                      <strong>Risk Assessment:</strong> {wayback.historical_risk_assessment}
                    </Typography>
                  </Alert>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* AI Analysis Highlights */}
        {llmAnalysis && (
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  AI Analysis Highlights
                </Typography>
                <Grid container spacing={2}>
                  {/* Good Highlights */}
                  {llmAnalysis.good_highlights && llmAnalysis.good_highlights.length > 0 && (
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" color="success.main" gutterBottom>
                        <TrendingUpIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        Strengths
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {llmAnalysis.good_highlights.map((highlight, index) => (
                          <Chip
                            key={index}
                            label={highlight}
                            color="success"
                            variant="outlined"
                            size="small"
                            sx={{ justifyContent: 'flex-start', textAlign: 'left' }}
                          />
                        ))}
                      </Box>
                    </Grid>
                  )}

                  {/* Bad Highlights */}
                  {llmAnalysis.bad_highlights && llmAnalysis.bad_highlights.length > 0 && (
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" color="error.main" gutterBottom>
                        <TrendingDownIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        Areas for Improvement
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {llmAnalysis.bad_highlights.map((highlight, index) => (
                          <Chip
                            key={index}
                            label={highlight}
                            color="error"
                            variant="outlined"
                            size="small"
                            sx={{ justifyContent: 'flex-start', textAlign: 'left' }}
                          />
                        ))}
                      </Box>
                    </Grid>
                  )}
                </Grid>

                {/* Suggested Niches */}
                {llmAnalysis.suggested_niches && llmAnalysis.suggested_niches.length > 0 && (
                  <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Suggested Content Niches
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {llmAnalysis.suggested_niches.map((niche, index) => (
                        <Chip
                          key={index}
                          label={niche}
                          color="primary"
                          variant="filled"
                          size="small"
                        />
                      ))}
                    </Box>
                  </Box>
                )}

                {/* Confidence Score */}
                {llmAnalysis.confidence_score && (
                  <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Analysis Confidence: {formatPercentage(llmAnalysis.confidence_score)}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={llmAnalysis.confidence_score * 100}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default ReportSummary;
