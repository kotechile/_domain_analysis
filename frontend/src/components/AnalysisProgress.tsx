import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  CircularProgress,
  Divider
} from '@mui/material';
import {
  CheckCircle,
  RadioButtonUnchecked,
  Schedule,
  TrendingUp,
  Assessment,
  Link as LinkIcon,
  Search,
  Language
} from '@mui/icons-material';
import { useApi } from '../services/api';
import { ProgressInfo } from '../services/api';

interface AnalysisProgressProps {
  domain: string;
  onComplete?: () => void;
}

interface AnalysisStage {
  name: string;
  completed: boolean;
  active: boolean;
}

const getAnalysisStages = (progress: any): AnalysisStage[] => {
  const stages = [
    { name: 'Essential Data Collection', key: 'essential' },
    { name: 'Detailed Data Collection', key: 'detailed' },
    { name: 'AI Analysis', key: 'ai' },
    { name: 'Finalization', key: 'finalization' }
  ];

  const currentPhase = progress.phase || 'essential';
  const completedOps = progress.completed_operations || 0;
  const totalOps = progress.total_operations || 4;

  return stages.map((stage, index) => {
    const isCompleted = index < completedOps;
    const isActive = index === completedOps && progress.status === 'in_progress';
    
    return {
      name: stage.name,
      completed: isCompleted,
      active: isActive
    };
  });
};

const getPhaseDescription = (phase: string): string => {
  const phaseDescriptions: { [key: string]: string } = {
    'essential': 'Collecting essential domain metrics (Domain Authority, traffic, backlinks, keywords)',
    'detailed': 'Gathering detailed backlink and keyword data',
    'ai': 'Generating AI-powered analysis and insights',
    'finalization': 'Finalizing report and saving results',
    'completed': 'Analysis completed successfully',
    'failed': 'Analysis failed'
  };
  
  return phaseDescriptions[phase] || 'Starting analysis...';
};

const getRealisticProgress = (progress: any): number => {
  // If we have a valid progress percentage, use it
  if (progress.progress_percentage > 0) {
    return progress.progress_percentage;
  }
  
  // Calculate progress based on completed operations
  const completedOps = progress.completed_operations || 0;
  const totalOps = progress.total_operations || 4;
  
  if (progress.status === 'completed') {
    return 100;
  }
  
  if (progress.status === 'failed') {
    return 0;
  }
  
  // Calculate progress based on operations
  const baseProgress = Math.floor((completedOps / totalOps) * 100);
  
  // Add some incremental progress within the current operation
  const currentOperationProgress = 25; // 25% per operation
  return Math.min(baseProgress + currentOperationProgress, 100);
};

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ domain, onComplete }) => {
  const api = useApi();
  const [progress, setProgress] = useState<ProgressInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const response = await api.getAnalysisProgress(domain);
        if (response.success && response.progress) {
          setProgress(response.progress);
          
          // Check if analysis is completed
          if (response.progress.status === 'completed' || response.progress.status === 'failed') {
            onComplete?.();
          }
        } else {
          setError(response.message || 'Failed to fetch progress');
        }
      } catch (err) {
        setError('Failed to fetch analysis progress');
        console.error('Progress fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchProgress();

    // Poll every 2 seconds
    const interval = setInterval(fetchProgress, 2000);

    return () => clearInterval(interval);
  }, [domain, api, onComplete]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <RadioButtonUnchecked color="error" />;
      case 'in_progress':
        return <CircularProgress size={20} />;
      default:
        return <Schedule color="action" />;
    }
  };

  const getOperationIcon = (operation: string) => {
    if (operation.includes('backlinks')) return <LinkIcon />;
    if (operation.includes('keywords')) return <Search />;
    if (operation.includes('referring domains')) return <Language />;
    if (operation.includes('AI')) return <Assessment />;
    return <TrendingUp />;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'in_progress':
        return 'primary';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!progress) {
    return (
      <Alert severity="warning" sx={{ m: 2 }}>
        No progress data available
      </Alert>
    );
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 2 }}>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            {getStatusIcon(progress.status)}
            <Typography variant="h6" sx={{ ml: 1 }}>
              Analysis Progress: {domain}
            </Typography>
            <Chip 
              label={progress.status.toUpperCase()} 
              color={getStatusColor(progress.status) as any}
              size="small"
              sx={{ ml: 'auto' }}
            />
          </Box>

          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Progress: {getRealisticProgress(progress)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {progress.completed_operations}/{progress.total_operations} operations
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={getRealisticProgress(progress)} 
              sx={{ height: 8, borderRadius: 4 }}
            />
            
            {/* Enhanced Progress Details */}
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                <strong>Current Phase:</strong> {getPhaseDescription(progress.phase)}
              </Typography>
              {progress.current_operation && (
                <Typography variant="body2" color="primary.main" sx={{ mb: 1 }}>
                  <strong>Current Task:</strong> {progress.current_operation}
                </Typography>
              )}
              {progress.status_message && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  <strong>Status:</strong> {progress.status_message}
                </Typography>
              )}
            </Box>
          </Box>

          {progress.status_message && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Current Status:</strong> {progress.status_message}
              </Typography>
            </Alert>
          )}

          {/* Analysis Stages */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Analysis Stages
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {getAnalysisStages(progress).map((stage, index) => (
                <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Box sx={{ 
                    width: 24, 
                    height: 24, 
                    borderRadius: '50%', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    backgroundColor: stage.completed ? 'success.main' : stage.active ? 'primary.main' : 'grey.300',
                    color: 'white',
                    fontSize: '0.75rem',
                    fontWeight: 'bold'
                  }}>
                    {stage.completed ? '✓' : index + 1}
                  </Box>
                  <Typography 
                    variant="body2" 
                    color={stage.completed ? 'success.main' : stage.active ? 'primary.main' : 'text.secondary'}
                    sx={{ fontWeight: stage.active ? 'bold' : 'normal' }}
                  >
                    {stage.name}
                  </Typography>
                  {stage.active && (
                    <Typography variant="caption" color="primary.main">
                      (In Progress)
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          </Box>

          {progress.detailed_status && progress.detailed_status.length > 0 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Detailed Status
              </Typography>
              <List dense>
                {progress.detailed_status.map((status, index) => (
                  <ListItem key={index} sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      {getOperationIcon(status)}
                    </ListItemIcon>
                    <ListItemText 
                      primary={status}
                      primaryTypographyProps={{ variant: 'body2' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {progress.estimated_time_remaining > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Estimated time remaining: {progress.estimated_time_remaining} seconds
              </Typography>
            </Box>
          )}

          {progress.last_updated && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Last updated: {new Date(progress.last_updated).toLocaleString()}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default AnalysisProgress;



