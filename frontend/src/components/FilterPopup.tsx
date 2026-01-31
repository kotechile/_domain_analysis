import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  IconButton,
  Stack,
  TextField,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import {
  Close as CloseIcon,
} from '@mui/icons-material';
import { useApi } from '../services/api';

interface FilterPopupProps {
  open: boolean;
  onClose: () => void;
  onApply: (filters: FilterValues) => void;
  initialFilters?: FilterValues;
}

export interface FilterValues {
  tlds?: string[];
  expirationFromDate?: string;
  expirationToDate?: string;
  scored?: boolean;
  minScore?: number;
  maxScore?: number;
}

const COMMON_TLDS = ['.com', '.io', '.ai', '.org', '.net', '.co', '.app', '.dev', '.tech', '.xyz'];

const FilterPopup: React.FC<FilterPopupProps> = ({ open, onClose, onApply, initialFilters }) => {
  const api = useApi();

  const [selectedTlds, setSelectedTlds] = useState<string[]>(initialFilters?.tlds || []);
  const [expirationFromDate, setExpirationFromDate] = useState<string>(initialFilters?.expirationFromDate || '');
  const [expirationToDate, setExpirationToDate] = useState<string>(initialFilters?.expirationToDate || '');
  const [scored, setScored] = useState<boolean>(initialFilters?.scored || false);
  const [minScore, setMinScore] = useState<string>(initialFilters?.minScore?.toString() || '');
  const [maxScore, setMaxScore] = useState<string>(initialFilters?.maxScore?.toString() || '');

  useEffect(() => {
    if (initialFilters) {
      setSelectedTlds(initialFilters.tlds || []);
      setExpirationFromDate(initialFilters.expirationFromDate || '');
      setExpirationToDate(initialFilters.expirationToDate || '');
      setScored(initialFilters.scored || false);
      setMinScore(initialFilters.minScore?.toString() || '');
      setMaxScore(initialFilters.maxScore?.toString() || '');
    }
  }, [initialFilters]);

  const handleTldToggle = (tld: string) => {
    setSelectedTlds(prev =>
      prev.includes(tld)
        ? prev.filter(t => t !== tld)
        : [...prev, tld]
    );
  };

  const handleAllTldsToggle = () => {
    setSelectedTlds([]);
  };

  const handleTodayClick = () => {
    const today = new Date().toISOString().split('T')[0];
    setExpirationFromDate(today);
    setExpirationToDate(today);
  };

  const handleTomorrowClick = () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];
    setExpirationFromDate(tomorrowStr);
    setExpirationToDate(tomorrowStr);
  };

  const handleApply = () => {
    const filters: FilterValues = {
      tlds: selectedTlds.length > 0 ? selectedTlds : undefined,
      expirationFromDate: expirationFromDate || undefined,
      expirationToDate: expirationToDate || undefined,
      scored: scored || undefined,
      minScore: minScore ? parseFloat(minScore) : undefined,
      maxScore: maxScore ? parseFloat(maxScore) : undefined,
    };
    onApply(filters);
    onClose();
  };

  const handleReset = () => {
    setSelectedTlds([]);
    setExpirationFromDate('');
    setExpirationToDate('');
    setScored(false);
    setMinScore('');
    setMaxScore('');
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#0C152B',
          borderRadius: '12px',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          color: '#FFFFFF',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Filters
        </Typography>
        <IconButton
          onClick={onClose}
          sx={{
            color: '#FFFFFF',
            '&:hover': {
              bgcolor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ mt: 2 }}>
        <Stack spacing={4}>
          {/* TLDs Section */}
          <Box>
            <Typography variant="subtitle1" sx={{ color: '#FFFFFF', mb: 2, fontWeight: 600 }}>
              TLDs
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
              {/* "All" option */}
              <FormControlLabel
                control={
                  <Checkbox
                    checked={selectedTlds.length === 0}
                    onChange={handleAllTldsToggle}
                    sx={{
                      color: '#FFFFFF',
                      '&.Mui-checked': {
                        color: '#1976d2',
                      },
                    }}
                  />
                }
                label="All"
                sx={{
                  color: '#FFFFFF',
                  fontWeight: 600,
                  '& .MuiFormControlLabel-label': {
                    fontSize: '0.875rem',
                  },
                }}
              />
              {COMMON_TLDS.map((tld) => (
                <FormControlLabel
                  key={tld}
                  control={
                    <Checkbox
                      checked={selectedTlds.includes(tld)}
                      onChange={() => handleTldToggle(tld)}
                      sx={{
                        color: '#FFFFFF',
                        '&.Mui-checked': {
                          color: '#1976d2',
                        },
                      }}
                    />
                  }
                  label={tld}
                  sx={{
                    color: '#FFFFFF',
                    '& .MuiFormControlLabel-label': {
                      fontSize: '0.875rem',
                    },
                  }}
                />
              ))}
            </Box>
          </Box>

          {/* Expiration Date Range Section */}
          <Box>
            <Typography variant="subtitle1" sx={{ color: '#FFFFFF', mb: 2, fontWeight: 600 }}>
              Expiration Date
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <TextField
                label="From"
                type="date"
                value={expirationFromDate}
                onChange={(e) => setExpirationFromDate(e.target.value)}
                InputLabelProps={{
                  shrink: true,
                  sx: { color: '#FFFFFF' },
                }}
                inputProps={{
                  min: new Date().toISOString().split('T')[0],
                }}
                sx={{
                  flex: 1,
                  minWidth: '150px',
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: 'transparent',
                    '& fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.3)',
                    },
                    '&:hover fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.5)',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#1976d2',
                    },
                    '& input': {
                      color: '#FFFFFF',
                      backgroundColor: 'transparent !important',
                    }
                  },
                  '& .MuiInputLabel-root': {
                    color: 'rgba(255, 255, 255, 0.7)',
                    backgroundColor: '#0C152B',
                    padding: '0 4px',
                  },
                  '& .MuiInputLabel-root.Mui-focused': {
                    color: '#1976d2',
                    backgroundColor: '#0C152B',
                  },
                  '& ::-webkit-calendar-picker-indicator': {
                    filter: 'invert(1)',
                  }
                }}
              />
              <TextField
                label="To"
                type="date"
                value={expirationToDate}
                onChange={(e) => setExpirationToDate(e.target.value)}
                InputLabelProps={{
                  shrink: true,
                  sx: { color: '#FFFFFF' },
                }}
                inputProps={{
                  min: expirationFromDate || new Date().toISOString().split('T')[0],
                }}
                sx={{
                  flex: 1,
                  minWidth: '150px',
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: 'transparent',
                    '& fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.3)',
                    },
                    '&:hover fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.5)',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#1976d2',
                    },
                    '& input': {
                      color: '#FFFFFF',
                      backgroundColor: 'transparent !important',
                    }
                  },
                  '& .MuiInputLabel-root': {
                    color: 'rgba(255, 255, 255, 0.7)',
                    backgroundColor: '#0C152B',
                    padding: '0 4px',
                  },
                  '& .MuiInputLabel-root.Mui-focused': {
                    color: '#1976d2',
                    backgroundColor: '#0C152B',
                  },
                  '& ::-webkit-calendar-picker-indicator': {
                    filter: 'invert(1)',
                  }
                }}
              />
              <Button
                variant="outlined"
                onClick={handleTodayClick}
                sx={{
                  color: '#FFFFFF',
                  borderColor: 'rgba(255, 255, 255, 0.3)',
                  '&:hover': {
                    borderColor: 'rgba(255, 255, 255, 0.5)',
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                Today
              </Button>
              <Button
                variant="outlined"
                onClick={handleTomorrowClick}
                sx={{
                  color: '#FFFFFF',
                  borderColor: 'rgba(255, 255, 255, 0.3)',
                  '&:hover': {
                    borderColor: 'rgba(255, 255, 255, 0.5)',
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                Tomorrow
              </Button>
            </Box>
          </Box>

          {/* Score Section */}
          <Box>
            <Typography variant="subtitle1" sx={{ color: '#FFFFFF', mb: 2, fontWeight: 600 }}>
              Score
            </Typography>
            <Stack spacing={2}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={scored}
                    onChange={(e) => setScored(e.target.checked)}
                    sx={{
                      color: '#FFFFFF',
                      '&.Mui-checked': {
                        color: '#1976d2',
                      },
                    }}
                  />
                }
                label="Only scored"
                sx={{
                  color: '#FFFFFF',
                }}
              />
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <TextField
                  label="Min Score"
                  type="number"
                  value={minScore}
                  onChange={(e) => setMinScore(e.target.value)}
                  InputLabelProps={{
                    sx: { color: '#FFFFFF' },
                  }}
                  inputProps={{
                    sx: { color: '#FFFFFF' },
                    min: 0,
                    max: 100,
                  }}
                  sx={{
                    flex: 1,
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: 'transparent',
                      '& fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.3)',
                      },
                      '&:hover fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.5)',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#1976d2',
                      },
                      '& input': {
                        color: '#FFFFFF',
                        backgroundColor: 'transparent !important',
                      }
                    },
                    '& .MuiInputLabel-root': {
                      color: 'rgba(255, 255, 255, 0.7)',
                      backgroundColor: '#0C152B',
                      padding: '0 4px',
                    },
                    '& .MuiInputLabel-root.Mui-focused': {
                      color: '#1976d2',
                      backgroundColor: '#0C152B',
                    }
                  }}
                />
                <TextField
                  label="Max Score"
                  type="number"
                  value={maxScore}
                  onChange={(e) => setMaxScore(e.target.value)}
                  InputLabelProps={{
                    sx: { color: '#FFFFFF' },
                  }}
                  inputProps={{
                    sx: { color: '#FFFFFF' },
                    min: 0,
                    max: 100,
                  }}
                  sx={{
                    flex: 1,
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: 'transparent',
                      '& fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.3)',
                      },
                      '&:hover fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.5)',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#1976d2',
                      },
                      '& input': {
                        color: '#FFFFFF',
                        backgroundColor: 'transparent !important',
                      }
                    },
                    '& .MuiInputLabel-root': {
                      color: 'rgba(255, 255, 255, 0.7)',
                      backgroundColor: '#0C152B',
                      padding: '0 4px',
                    },
                    '& .MuiInputLabel-root.Mui-focused': {
                      color: '#1976d2',
                      backgroundColor: '#0C152B',
                    }
                  }}
                />
              </Box>
            </Stack>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 3, borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <Button
          onClick={handleReset}
          sx={{
            color: '#FFFFFF',
            '&:hover': {
              bgcolor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          Reset
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button
          onClick={onClose}
          sx={{
            color: '#FFFFFF',
            '&:hover': {
              bgcolor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          Cancel
        </Button>
        <Button
          onClick={handleApply}
          variant="contained"
          sx={{
            bgcolor: '#1976d2',
            color: '#FFFFFF',
            '&:hover': {
              bgcolor: '#1565c0',
            },
          }}
        >
          Apply
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FilterPopup;



