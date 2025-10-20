import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  LinearProgress,
  Divider,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Lightbulb as LightbulbIcon,
  Assessment as AssessmentIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';

import { LLMAnalysis as LLMAnalysisType } from '../services/api';

interface LLMAnalysisProps {
  analysis: LLMAnalysisType | undefined;
}

const LLMAnalysis: React.FC<LLMAnalysisProps> = ({ analysis }) => {
  if (!analysis) {
    return (
      <Alert severity="info">
        No AI analysis available for this domain.
      </Alert>
    );
  }

  const formatPercentage = (num: number | undefined) => {
    if (num === undefined || num === null) return 'N/A';
    return `${(num * 100).toFixed(1)}%`;
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        AI-Powered Analysis
      </Typography>

      {/* Summary */}
      {analysis.summary && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Executive Summary
            </Typography>
            <Typography variant="body1" paragraph>
              {analysis.summary}
            </Typography>
            {analysis.confidence_score && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Analysis Confidence: {formatPercentage(analysis.confidence_score)}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={analysis.confidence_score * 100}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      <Grid container spacing={3}>
        {/* Good Highlights */}
        {analysis.good_highlights && analysis.good_highlights.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" color="success.main" gutterBottom>
                  <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Strengths
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {analysis.good_highlights.map((highlight, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                      <CheckCircleIcon color="success" fontSize="small" sx={{ mt: 0.5, flexShrink: 0 }} />
                      <Typography variant="body2">
                        {highlight}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Bad Highlights */}
        {analysis.bad_highlights && analysis.bad_highlights.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" color="error.main" gutterBottom>
                  <TrendingDownIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Areas for Improvement
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {analysis.bad_highlights.map((highlight, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                      <CancelIcon color="error" fontSize="small" sx={{ mt: 0.5, flexShrink: 0 }} />
                      <Typography variant="body2">
                        {highlight}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Suggested Niches */}
        {analysis.suggested_niches && analysis.suggested_niches.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <LightbulbIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Suggested Content Niches
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Based on the domain's existing SEO foundation and keyword profile, these niches could be developed:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {analysis.suggested_niches.map((niche, index) => (
                    <Chip
                      key={index}
                      label={niche}
                      color="primary"
                      variant="filled"
                      size="medium"
                      sx={{ mb: 1 }}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Advantages/Disadvantages Table */}
        {analysis.advantages_disadvantages_table && analysis.advantages_disadvantages_table.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Investment Analysis
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Type</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Supporting Metric</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {analysis.advantages_disadvantages_table.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Chip
                              label={item.type === 'advantage' ? 'Advantage' : 'Disadvantage'}
                              color={item.type === 'advantage' ? 'success' : 'error'}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {item.description}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {item.metric}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Analysis Methodology */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Analysis Methodology
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            This analysis was generated using advanced AI technology that processes:
          </Typography>
          <Box component="ul" sx={{ pl: 2, m: 0 }}>
            <li>
              <Typography variant="body2" color="text.secondary">
                SEO metrics including domain rating, organic traffic, and backlink profiles
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Keyword data and search volume information
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Historical domain data from the Wayback Machine
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Industry best practices and competitive analysis patterns
              </Typography>
            </li>
          </Box>
          <Divider sx={{ my: 2 }} />
          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            Note: This analysis is for informational purposes only and should not be considered as investment advice.
            Always conduct your own due diligence before making domain investment decisions.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default LLMAnalysis;
