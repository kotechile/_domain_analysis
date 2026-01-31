import React from 'react';
import {
  Box,
  LinearProgress,
  Typography,
  Chip,
  Card,
  CardContent,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Schedule,
  Cancel
} from '@mui/icons-material';

export interface ProgressInfo {
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  phase: 'essential' | 'detailed' | 'ai_analysis' | 'completed';
  progress_percentage: number;
  estimated_time_remaining?: number;
  current_operation?: string;
  completed_operations?: string[];
  error_message?: string;
}

interface ProgressIndicatorProps {
  progress: ProgressInfo;
  onCancel?: () => void;
  showDetails?: boolean;
}

const getStatusColor = (status: ProgressInfo['status']) => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'failed':
      return 'error';
    case 'cancelled':
      return 'secondary';
    case 'in_progress':
      return 'primary';
    case 'pending':
      return 'warning';
    default:
      return 'secondary';
  }
};

const getStatusIcon = (status: ProgressInfo['status']) => {
  switch (status) {
    case 'completed':
      return <CheckCircle />;
    case 'failed':
      return <Error />;
    case 'cancelled':
      return <Cancel />;
    case 'in_progress':
      return <Schedule />;
    case 'pending':
      return <Schedule />;
    default:
      return <Schedule />;
  }
};

const getPhaseLabel = (phase: ProgressInfo['phase']) => {
  switch (phase) {
    case 'essential':
      return 'Essential Data';
    case 'detailed':
      return 'Detailed Data';
    case 'ai_analysis':
      return 'AI Analysis';
    case 'completed':
      return 'Completed';
    default:
      return phase;
  }
};

const formatTimeRemaining = (seconds?: number) => {
  if (!seconds) return '';
  
  if (seconds < 60) {
    return `${seconds}s`;
  } else if (seconds < 3600) {
    const minutes = Math.ceil(seconds / 60);
    return `${minutes}m`;
  } else {
    const hours = Math.ceil(seconds / 3600);
    return `${hours}h`;
  }
};

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  progress,
  onCancel,
  showDetails = true
}) => {
  const {
    status,
    phase,
    progress_percentage,
    estimated_time_remaining,
    current_operation,
    completed_operations = [],
    error_message
  } = progress;

  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';
  const isCancelled = status === 'cancelled';
  const isInProgress = status === 'in_progress';

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            {getStatusIcon(status)}
            <Typography variant="h6" component="h3">
              Analysis Progress
            </Typography>
            <Chip
              label={getPhaseLabel(phase)}
              color={getStatusColor(status)}
              size="small"
            />
          </Box>
          
          {isInProgress && onCancel && (
            <Tooltip title="Cancel Analysis">
              <IconButton onClick={onCancel} size="small">
                <Cancel />
              </IconButton>
            </Tooltip>
          )}
        </Box>

        {/* Progress Bar */}
        <Box mb={2}>
          <LinearProgress
            variant="determinate"
            value={progress_percentage}
            color={getStatusColor(status)}
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Box display="flex" justifyContent="space-between" mt={1}>
            <Typography variant="body2" color="text.secondary">
              {progress_percentage}% Complete
            </Typography>
            {estimated_time_remaining && (
              <Typography variant="body2" color="text.secondary">
                {formatTimeRemaining(estimated_time_remaining)} remaining
              </Typography>
            )}
          </Box>
        </Box>

        {/* Current Operation */}
        {current_operation && (
          <Box mb={2}>
            <Typography variant="body2" color="text.secondary">
              Current: {current_operation}
            </Typography>
          </Box>
        )}

        {/* Error Message */}
        {isFailed && error_message && (
          <Box mb={2}>
            <Typography variant="body2" color="error">
              Error: {error_message}
            </Typography>
          </Box>
        )}

        {/* Detailed Operations */}
        {showDetails && completed_operations.length > 0 && (
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Completed Operations:
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={0.5}>
              {completed_operations.map((operation, index) => (
                <Chip
                  key={index}
                  label={operation}
                  size="small"
                  color="success"
                  icon={<CheckCircle />}
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Status Messages */}
        {isCompleted && (
          <Typography variant="body2" color="success.main" sx={{ mt: 1 }}>
            Analysis completed successfully!
          </Typography>
        )}

        {isCancelled && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Analysis was cancelled.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default ProgressIndicator;
