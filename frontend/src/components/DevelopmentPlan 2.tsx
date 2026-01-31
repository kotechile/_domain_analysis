import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Divider,
  Grid,
  Paper,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Lightbulb as LightbulbIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Flag as TargetIcon,
  Analytics as AnalyticsIcon,
  ContentCopy as ContentCopyIcon,
  Launch as LaunchIcon,
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import { useApi, DomainAnalysisReport } from '../services/api';

interface DevelopmentPlanProps {
  domain: string;
  reportData: DomainAnalysisReport;
}

interface DevelopmentPlanResponse {
  plan: {
    title: string;
    description: string;
    strategies: Array<{
      id: string;
      title: string;
      description: string;
      priority: 'high' | 'medium' | 'low';
      estimated_effort: 'low' | 'medium' | 'high';
      expected_impact: 'low' | 'medium' | 'high';
      timeline: string;
      steps: string[];
      keywords: string[];
      expected_traffic_increase: string;
    }>;
    timeline: {
      phase: string;
      duration: string;
      focus: string;
    }[];
    success_metrics: string[];
  };
}

const DevelopmentPlan: React.FC<DevelopmentPlanProps> = ({ domain, reportData }) => {
  const api = useApi();
  const [plan, setPlan] = useState<DevelopmentPlanResponse['plan'] | null>(null);

  const generatePlanMutation = useMutation({
    mutationFn: () => api.generateDevelopmentPlan(domain),
    onSuccess: (data) => {
      setPlan(data.plan);
    },
  });

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getEffortColor = (effort: string) => {
    switch (effort) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'error';
      default: return 'default';
    }
  };

  if (generatePlanMutation.isPending) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
        <CircularProgress size={40} sx={{ mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Generating Development Plan...
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Analyzing your domain's current performance and creating actionable strategies
        </Typography>
      </Box>
    );
  }

  if (generatePlanMutation.isError) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Failed to Generate Development Plan
        </Typography>
        <Typography variant="body2">
          {generatePlanMutation.error?.message || 'An error occurred while generating the development plan.'}
        </Typography>
        <Button
          variant="outlined"
          onClick={() => generatePlanMutation.reset()}
          sx={{ mt: 2 }}
        >
          Try Again
        </Button>
      </Alert>
    );
  }

  if (!plan) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <TrendingUpIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h4" gutterBottom>
          Domain Development Plan
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 600, mx: 'auto' }}>
          Get personalized strategies to grow your domain's traffic based on your current backlinks, 
          keywords, and competitive analysis. Our AI will analyze your data and provide actionable 
          recommendations tailored to your domain.
        </Typography>
        
        <Box sx={{ mb: 4 }}>
          <Grid container spacing={2} justifyContent="center">
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <AnalyticsIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                <Typography variant="h6" gutterBottom>Data-Driven</Typography>
                <Typography variant="body2" color="text.secondary">
                  Based on your actual backlinks and keyword data
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <TargetIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                <Typography variant="h6" gutterBottom>Actionable</Typography>
                <Typography variant="body2" color="text.secondary">
                  Specific steps you can implement immediately
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <TrendingUpIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                <Typography variant="h6" gutterBottom>Growth-Focused</Typography>
                <Typography variant="body2" color="text.secondary">
                  Strategies designed to increase traffic
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </Box>

        <Button
          variant="contained"
          size="large"
          startIcon={<LightbulbIcon />}
          onClick={() => generatePlanMutation.mutate()}
          sx={{ minWidth: 250 }}
        >
          Generate Development Plan
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          {plan.title}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {plan.description}
        </Typography>
      </Box>

      {/* Timeline Overview */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ScheduleIcon color="primary" />
            Implementation Timeline
          </Typography>
          <Stepper orientation="vertical">
            {plan.timeline.map((phase, index) => (
              <Step key={index} active>
                <StepLabel>{phase.phase}</StepLabel>
                <StepContent>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    <strong>Duration:</strong> {phase.duration}
                  </Typography>
                  <Typography variant="body2">
                    {phase.focus}
                  </Typography>
                </StepContent>
              </Step>
            ))}
          </Stepper>
        </CardContent>
      </Card>

      {/* Development Strategies */}
      <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
        Development Strategies
      </Typography>

      {plan.strategies.map((strategy, index) => (
        <Card key={strategy.id} sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="h6" sx={{ flex: 1 }}>
                {strategy.title}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip 
                  label={`Priority: ${strategy.priority}`} 
                  color={getPriorityColor(strategy.priority) as any}
                  size="small"
                />
                <Chip 
                  label={`Effort: ${strategy.estimated_effort}`} 
                  color={getEffortColor(strategy.estimated_effort) as any}
                  size="small"
                />
                <Chip 
                  label={`Impact: ${strategy.expected_impact}`} 
                  color={getImpactColor(strategy.expected_impact) as any}
                  size="small"
                />
              </Box>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {strategy.description}
            </Typography>

            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <ScheduleIcon color="action" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Timeline: {strategy.timeline}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <TrendingUpIcon color="action" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Expected Traffic: {strategy.expected_traffic_increase}
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CheckCircleIcon color="primary" fontSize="small" />
              Implementation Steps
            </Typography>
            <List dense>
              {strategy.steps.map((step, stepIndex) => (
                <ListItem key={stepIndex} sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <Typography variant="body2" color="primary" sx={{ fontWeight: 'bold' }}>
                      {stepIndex + 1}.
                    </Typography>
                  </ListItemIcon>
                  <ListItemText 
                    primary={step}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      ))}

      {/* Success Metrics */}
      <Card sx={{ mt: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AnalyticsIcon color="primary" />
            Success Metrics
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Track these metrics to measure the success of your development plan:
          </Typography>
          <List dense>
            {plan.success_metrics.map((metric, index) => (
              <ListItem key={index} sx={{ py: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <TargetIcon color="primary" fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary={metric}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center' }}>
        <Button
          variant="outlined"
          startIcon={<ContentCopyIcon />}
          onClick={() => {
            const planText = `${plan.title}\n\n${plan.description}\n\nStrategies:\n${plan.strategies.map(s => `- ${s.title}: ${s.description}`).join('\n')}`;
            navigator.clipboard.writeText(planText);
          }}
        >
          Copy Plan
        </Button>
        <Button
          variant="contained"
          startIcon={<LaunchIcon />}
          onClick={() => generatePlanMutation.mutate()}
        >
          Generate New Plan
        </Button>
      </Box>
    </Box>
  );
};

export default DevelopmentPlan;
