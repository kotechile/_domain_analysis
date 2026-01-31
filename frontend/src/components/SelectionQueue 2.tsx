import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  Stack,
} from '@mui/material';
import {
  Clear as ClearIcon,
  PlayArrow as PlayArrowIcon,
} from '@mui/icons-material';

interface SelectionQueueProps {
  selectedDomains: string[];
  onClear: () => void;
  onAnalyze: () => void;
  isAnalyzing?: boolean;
}

const SelectionQueue: React.FC<SelectionQueueProps> = ({
  selectedDomains,
  onClear,
  onAnalyze,
  isAnalyzing = false,
}) => {
  if (selectedDomains.length === 0) {
    return null;
  }

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Selection Queue
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Chip
            label={`${selectedDomains.length} domain${selectedDomains.length !== 1 ? 's' : ''} selected`}
            color="primary"
          />
          <Button
            variant="outlined"
            size="small"
            startIcon={<ClearIcon />}
            onClick={onClear}
            disabled={isAnalyzing}
          >
            Clear
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={<PlayArrowIcon />}
            onClick={onAnalyze}
            disabled={isAnalyzing || selectedDomains.length === 0}
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze in Bulk'}
          </Button>
        </Box>
      </Box>

      {/* Selected Domains List */}
      <Box sx={{ maxHeight: 150, overflowY: 'auto' }}>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {selectedDomains.map((domain) => (
            <Chip
              key={domain}
              label={domain}
              size="small"
              onDelete={undefined}
            />
          ))}
        </Stack>
      </Box>
    </Paper>
  );
};

export default SelectionQueue;
