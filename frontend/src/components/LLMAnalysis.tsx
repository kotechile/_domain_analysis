import React, { useState } from 'react';
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
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  useTheme,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Lightbulb as LightbulbIcon,
  Assessment as AssessmentIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  ShoppingCart as ShoppingCartIcon,
  Warning as WarningIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  Business as BusinessIcon,
  Article as ArticleIcon,
  Link as LinkIcon,
} from '@mui/icons-material';

import { LLMAnalysis as LLMAnalysisType, useApi } from '../services/api';

interface LLMAnalysisProps {
  analysis: LLMAnalysisType | undefined;
  domain: string;
  detailedDataAvailable?: {
    backlinks: boolean;
    keywords: boolean;
    referring_domains: boolean;
  };
  backlinkQualityAssessment?: {
    overall_quality_score: number;
    high_dr_percentage: number;
    link_diversity_score: number;
    relevance_score: number;
    velocity_score: number;
    geographic_diversity: number;
    anchor_text_diversity: number;
    quality_concerns: string[];
    quality_strengths: string[];
  };
  investmentRecommendation?: {
    overall_score: number;
    risk_level: string;
    potential_return: string;
    key_factors: string[];
    improvement_priorities: string[];
  };
}

const LLMAnalysis: React.FC<LLMAnalysisProps> = ({ 
  analysis, 
  domain, 
  detailedDataAvailable,
  backlinkQualityAssessment,
  investmentRecommendation 
}) => {
  const theme = useTheme();

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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          AI-Powered Analysis
        </Typography>
      </Box>

      {/* Buy Recommendation */}
      {analysis.buy_recommendation && (
        <Card sx={{ mb: 3, border: 2, borderColor: analysis.buy_recommendation.recommendation === 'BUY' ? 'success.main' : 
                   analysis.buy_recommendation.recommendation === 'CAUTION' ? 'warning.main' : 'error.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h5" gutterBottom>
                <ShoppingCartIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Domain Purchase Recommendation
              </Typography>
              <Chip
                label={analysis.buy_recommendation.recommendation}
                color={analysis.buy_recommendation.recommendation === 'BUY' ? 'success' : 
                       analysis.buy_recommendation.recommendation === 'CAUTION' ? 'warning' : 'error'}
                size="medium"
                sx={{ fontSize: '1.1rem', fontWeight: 'bold' }}
              />
            </Box>
            <Typography variant="body1" paragraph>
              {analysis.buy_recommendation.reasoning}
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <Box sx={{ 
                  textAlign: 'center', 
                  p: 2, 
                  bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'grey.50',
                  borderRadius: 2,
                  border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}`
                }}>
                  <Typography variant="h6" color="primary">
                    {formatPercentage(analysis.buy_recommendation.confidence)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Confidence
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ 
                  textAlign: 'center', 
                  p: 2, 
                  bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'grey.50',
                  borderRadius: 2,
                  border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}`
                }}>
                  <Chip
                    label={analysis.buy_recommendation.risk_level.toUpperCase()}
                    color={analysis.buy_recommendation.risk_level === 'low' ? 'success' : 
                           analysis.buy_recommendation.risk_level === 'medium' ? 'warning' : 'error'}
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    Risk Level
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ 
                  textAlign: 'center', 
                  p: 2, 
                  bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'grey.50',
                  borderRadius: 2,
                  border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}`
                }}>
                  <Typography variant="h6" color="success.main">
                    {analysis.buy_recommendation.potential_value.toUpperCase()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Potential Value
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

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
        {/* Valuable Assets */}
        {analysis.valuable_assets && analysis.valuable_assets.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" color="success.main" gutterBottom>
                  <ThumbUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Valuable Assets
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {analysis.valuable_assets.map((asset, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                      <CheckCircleIcon color="success" fontSize="small" sx={{ mt: 0.5, flexShrink: 0 }} />
                      <Typography variant="body2">
                        {asset}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Major Concerns */}
        {analysis.major_concerns && analysis.major_concerns.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" color="error.main" gutterBottom>
                  <WarningIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Major Concerns
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {analysis.major_concerns.map((concern, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                      <CancelIcon color="error" fontSize="small" sx={{ mt: 0.5, flexShrink: 0 }} />
                      <Typography variant="body2">
                        {concern}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Legacy Good/Bad Highlights for backward compatibility */}
        {analysis.good_highlights && analysis.good_highlights.length > 0 && !analysis.valuable_assets && (
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

        {/* Legacy Bad Highlights for backward compatibility */}
        {analysis.bad_highlights && analysis.bad_highlights.length > 0 && !analysis.major_concerns && (
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

        {/* Content Strategy */}
        {analysis.content_strategy && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <ArticleIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Content Strategy for New Website
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      Primary Niche
                    </Typography>
                    <Chip
                      label={analysis.content_strategy.primary_niche}
                      color="primary"
                      variant="filled"
                      size="medium"
                      sx={{ mb: 2 }}
                    />
                    {analysis.content_strategy.secondary_niches && analysis.content_strategy.secondary_niches.length > 0 && (
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Secondary Niches
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {analysis.content_strategy.secondary_niches.map((niche, index) => (
                            <Chip
                              key={index}
                              label={niche}
                              color="secondary"
                              variant="outlined"
                              size="small"
                              sx={{ mb: 1 }}
                            />
                          ))}
                        </Box>
                      </Box>
                    )}
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      Target Keywords
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {analysis.content_strategy.target_keywords && analysis.content_strategy.target_keywords.map((keyword, index) => (
                        <Chip
                          key={index}
                          label={keyword}
                          color="info"
                          variant="outlined"
                          size="small"
                          sx={{ mb: 1 }}
                        />
                      ))}
                    </Box>
                  </Grid>
                  {analysis.content_strategy.first_articles && analysis.content_strategy.first_articles.length > 0 && (
                    <Grid item xs={12}>
                      <Typography variant="subtitle1" gutterBottom>
                        First Articles to Publish
                      </Typography>
                      <List dense>
                        {analysis.content_strategy.first_articles.map((article, index) => (
                          <ListItem key={index}>
                            <ListItemIcon>
                              <ArticleIcon fontSize="small" />
                            </ListItemIcon>
                            <ListItemText primary={article} />
                          </ListItem>
                        ))}
                      </List>
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Legacy Suggested Niches for backward compatibility */}
        {analysis.suggested_niches && analysis.suggested_niches.length > 0 && !analysis.content_strategy && (
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

        {/* Action Plan */}
        {analysis.action_plan && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <BusinessIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Action Plan for Domain Buyers
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle1" gutterBottom color="primary">
                      Immediate Actions
                    </Typography>
                    <List dense>
                      {analysis.action_plan.immediate_actions && analysis.action_plan.immediate_actions.map((action, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <CheckCircleIcon color="primary" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={action} />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle1" gutterBottom color="warning.main">
                      First Month
                    </Typography>
                    <List dense>
                      {analysis.action_plan.first_month && analysis.action_plan.first_month.map((action, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <LightbulbIcon color="warning" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={action} />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle1" gutterBottom color="info.main">
                      Long-term Strategy
                    </Typography>
                    <List dense>
                      {analysis.action_plan.long_term_strategy && analysis.action_plan.long_term_strategy.map((action, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <TrendingUpIcon color="info" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={action} />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Pros and Cons */}
        {analysis.pros_and_cons && analysis.pros_and_cons.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Pros and Cons Analysis
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Type</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Impact</TableCell>
                        <TableCell>Example</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {analysis.pros_and_cons.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Chip
                              label={item.type === 'pro' ? 'Pro' : 'Con'}
                              color={item.type === 'pro' ? 'success' : 'error'}
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
                            <Chip
                              label={item.impact}
                              color={item.impact === 'high' ? 'error' : item.impact === 'medium' ? 'warning' : 'success'}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {item.example}
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

        {/* Legacy Advantages/Disadvantages Table for backward compatibility */}
        {analysis.advantages_disadvantages_table && analysis.advantages_disadvantages_table.length > 0 && !analysis.pros_and_cons && (
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

      {/* Backlink Quality Assessment */}
      {backlinkQualityAssessment && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Backlink Quality Assessment
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Overall Quality Score
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{ width: '100%', mr: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={backlinkQualityAssessment.overall_quality_score * 10}
                        sx={{ height: 10, borderRadius: 5 }}
                      />
                    </Box>
                    <Typography variant="h6" color="primary">
                      {backlinkQualityAssessment.overall_quality_score}/10
                    </Typography>
                  </Box>
                </Box>
                
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      High DR Links
                    </Typography>
                    <Typography variant="h6">
                      {backlinkQualityAssessment.high_dr_percentage}%
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Link Diversity
                    </Typography>
                    <Typography variant="h6">
                      {backlinkQualityAssessment.link_diversity_score}/10
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Relevance Score
                    </Typography>
                    <Typography variant="h6">
                      {backlinkQualityAssessment.relevance_score}/10
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Anchor Diversity
                    </Typography>
                    <Typography variant="h6">
                      {backlinkQualityAssessment.anchor_text_diversity}/10
                    </Typography>
                  </Grid>
                </Grid>
              </Grid>
              
              <Grid item xs={12} md={6}>
                {backlinkQualityAssessment.quality_strengths && backlinkQualityAssessment.quality_strengths.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="h6" color="success.main" gutterBottom>
                      Quality Strengths
                    </Typography>
                    {backlinkQualityAssessment.quality_strengths.map((strength, index) => (
                      <Chip
                        key={index}
                        label={strength}
                        color="success"
                        size="small"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    ))}
                  </Box>
                )}
                
                {backlinkQualityAssessment.quality_concerns && backlinkQualityAssessment.quality_concerns.length > 0 && (
                  <Box>
                    <Typography variant="h6" color="error.main" gutterBottom>
                      Quality Concerns
                    </Typography>
                    {backlinkQualityAssessment.quality_concerns.map((concern, index) => (
                      <Chip
                        key={index}
                        label={concern}
                        color="error"
                        size="small"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    ))}
                  </Box>
                )}
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Investment Recommendation */}
      {investmentRecommendation && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Investment Recommendation
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                  <Typography variant="h3" color="primary">
                    {investmentRecommendation.overall_score}/10
                  </Typography>
                  <Typography variant="h6" gutterBottom>
                    Overall Score
                  </Typography>
                  <Chip
                    label={investmentRecommendation.risk_level.toUpperCase()}
                    color={investmentRecommendation.risk_level === 'low' ? 'success' : 
                           investmentRecommendation.risk_level === 'medium' ? 'warning' : 'error'}
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    Risk Level
                  </Typography>
                </Box>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                  <Typography variant="h4" color="success.main">
                    {investmentRecommendation.potential_return.toUpperCase()}
                  </Typography>
                  <Typography variant="h6" gutterBottom>
                    Potential Return
                  </Typography>
                </Box>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Key Factors
                  </Typography>
                  {investmentRecommendation.key_factors.map((factor, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                      <CheckCircleIcon color="primary" fontSize="small" sx={{ mt: 0.5, flexShrink: 0 }} />
                      <Typography variant="body2">
                        {factor}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Grid>
            </Grid>
            
            {investmentRecommendation.improvement_priorities && investmentRecommendation.improvement_priorities.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Improvement Priorities
                </Typography>
                {investmentRecommendation.improvement_priorities.map((priority, index) => (
                  <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                    <LightbulbIcon color="warning" fontSize="small" sx={{ mt: 0.5, flexShrink: 0 }} />
                    <Typography variant="body2">
                      {priority}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Detailed Data Availability Status */}
      {detailedDataAvailable && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Detailed Data Status
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircleIcon color={detailedDataAvailable.backlinks ? 'success' : 'disabled'} />
                  <Typography variant="body2">
                    Backlinks Data: {detailedDataAvailable.backlinks ? 'Available' : 'Not Available'}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircleIcon color={detailedDataAvailable.keywords ? 'success' : 'disabled'} />
                  <Typography variant="body2">
                    Keywords Data: {detailedDataAvailable.keywords ? 'Available' : 'Not Available'}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircleIcon color={detailedDataAvailable.referring_domains ? 'success' : 'disabled'} />
                  <Typography variant="body2">
                    Referring Domains: {detailedDataAvailable.referring_domains ? 'Available' : 'Not Available'}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default LLMAnalysis;
