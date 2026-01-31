import React, { useState, useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Grid,
  Paper,
  Chip,
  IconButton,
  Collapse,
  Divider,
} from '@mui/material';
import {
  Close as CloseIcon,
  Analytics as AnalyticsIcon,
  Link as LinkIcon,
  TrendingUp as TrendingUpIcon,
  Language as LanguageIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Code as CodeIcon,
  Public as PublicIcon,
  Warning as WarningIcon,
  Domain as DomainIcon,
} from '@mui/icons-material';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useApi } from '../services/api';

interface DataForSEOPopupProps {
  open: boolean;
  onClose: () => void;
  domain: string;
  pageStatistics?: any; // JSON data from page_statistics field
}

// Recursive component to render JSON in a formatted way
const JSONViewer: React.FC<{ data: any; level?: number; path?: string }> = ({ 
  data, 
  level = 0,
  path = ''
}) => {
  const [expanded, setExpanded] = useState<{ [key: string]: boolean }>({});

  const toggleExpand = (key: string) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const getValueColor = (value: any): string => {
    if (typeof value === 'number') return '#4CAF50';
    if (typeof value === 'string') return '#FF9800';
    if (typeof value === 'boolean') return '#2196F3';
    if (value === null) return '#9E9E9E';
    return '#FFFFFF';
  };

  const formatValue = (value: any): string => {
    if (value === null) return 'null';
    if (typeof value === 'string') return `"${value}"`;
    if (typeof value === 'number') return value.toString();
    if (typeof value === 'boolean') return value.toString();
    return '';
  };

  if (data === null || data === undefined) {
    return (
      <Typography component="span" sx={{ color: '#9E9E9E', fontStyle: 'italic' }}>
        null
      </Typography>
    );
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return (
        <Typography component="span" sx={{ color: '#9E9E9E', fontStyle: 'italic' }}>
          []
        </Typography>
      );
    }

    const key = path || 'root';
    const isExpanded = expanded[key] ?? level < 2; // Auto-expand first 2 levels

    return (
      <Box sx={{ ml: level * 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' },
            py: 0.5,
            px: 1,
            borderRadius: '4px',
          }}
          onClick={() => toggleExpand(key)}
        >
          {isExpanded ? (
            <ExpandLessIcon sx={{ color: '#66CCFF', fontSize: 16, mr: 0.5 }} />
          ) : (
            <ExpandMoreIcon sx={{ color: '#66CCFF', fontSize: 16, mr: 0.5 }} />
          )}
          <Typography component="span" sx={{ color: '#66CCFF', fontWeight: 600, mr: 1 }}>
            Array [{data.length}]
          </Typography>
        </Box>
        <Collapse in={isExpanded}>
          <Box sx={{ ml: 3, borderLeft: '1px solid rgba(102, 204, 255, 0.3)', pl: 2, mt: 0.5 }}>
            {data.map((item, index) => (
              <Box key={index} sx={{ mb: 1 }}>
                <Typography component="span" sx={{ color: '#9E9E9E', fontSize: '0.85rem', mr: 1 }}>
                  [{index}]:
                </Typography>
                <JSONViewer data={item} level={level + 1} path={`${key}[${index}]`} />
              </Box>
            ))}
          </Box>
        </Collapse>
      </Box>
    );
  }

  if (typeof data === 'object') {
    const keys = Object.keys(data);
    if (keys.length === 0) {
      return (
        <Typography component="span" sx={{ color: '#9E9E9E', fontStyle: 'italic' }}>
          {'{}'}
        </Typography>
      );
    }

    const key = path || 'root';
    const isExpanded = expanded[key] ?? level < 2; // Auto-expand first 2 levels

    return (
      <Box sx={{ ml: level * 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' },
            py: 0.5,
            px: 1,
            borderRadius: '4px',
          }}
          onClick={() => toggleExpand(key)}
        >
          {isExpanded ? (
            <ExpandLessIcon sx={{ color: '#66CCFF', fontSize: 16, mr: 0.5 }} />
          ) : (
            <ExpandMoreIcon sx={{ color: '#66CCFF', fontSize: 16, mr: 0.5 }} />
          )}
          <Typography component="span" sx={{ color: '#66CCFF', fontWeight: 600, mr: 1 }}>
            Object {'{'} {keys.length} {keys.length === 1 ? 'key' : 'keys'} {'}'}
          </Typography>
        </Box>
        <Collapse in={isExpanded}>
          <Box sx={{ ml: 3, borderLeft: '1px solid rgba(102, 204, 255, 0.3)', pl: 2, mt: 0.5 }}>
            {keys.map((objKey) => {
              const value = data[objKey];
              const isComplex = typeof value === 'object' && value !== null;
              const itemPath = `${key}.${objKey}`;
              
              return (
                <Box key={objKey} sx={{ mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                    <Typography
                      component="span"
                      sx={{
                        color: '#66CCFF',
                        fontWeight: 500,
                        mr: 1,
                        minWidth: '150px',
                        fontSize: '0.9rem',
                      }}
                    >
                      "{objKey}":
                    </Typography>
                    {isComplex ? (
                      <Box sx={{ flex: 1 }}>
                        <JSONViewer data={value} level={level + 1} path={itemPath} />
                      </Box>
                    ) : (
                      <Typography
                        component="span"
                        sx={{
                          color: getValueColor(value),
                          fontFamily: 'monospace',
                          fontSize: '0.9rem',
                        }}
                      >
                        {formatValue(value)}
                      </Typography>
                    )}
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Collapse>
      </Box>
    );
  }

  // Primitive value
  return (
    <Typography
      component="span"
      sx={{
        color: getValueColor(data),
        fontFamily: 'monospace',
        fontSize: '0.9rem',
      }}
    >
      {formatValue(data)}
    </Typography>
  );
};

// Color palette for charts
const CHART_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // orange
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange-600
  '#6366f1', // indigo
];

const DataForSEOPopup: React.FC<DataForSEOPopupProps> = ({
  open,
  onClose,
  domain,
  pageStatistics,
}) => {
  const [rawDataExpanded, setRawDataExpanded] = useState(false);
  const hasData = pageStatistics && typeof pageStatistics === 'object';

  // Extract and format chart data
  const chartData = useMemo(() => {
    if (!hasData) return { tldData: [], countryData: [] };

    const tldData = pageStatistics.referring_links_tld
      ? Object.entries(pageStatistics.referring_links_tld).map(([name, value]) => ({
          name: name || 'unknown',
          value: Number(value) || 0,
        }))
      : [];

    const countryData = pageStatistics.referring_links_countries
      ? Object.entries(pageStatistics.referring_links_countries)
          .map(([name, value]) => ({
            name: name || 'unknown',
            value: Number(value) || 0,
          }))
          .sort((a, b) => b.value - a.value) // Sort by value descending
      : [];

    return { tldData, countryData };
  }, [pageStatistics, hasData]);

  // Get summary values
  const summary = useMemo(() => {
    if (!hasData) return null;

    return {
      backlinks: pageStatistics.backlinks ?? 0,
      referringDomains: pageStatistics.referring_domains ?? 0,
      referringPages: pageStatistics.referring_pages ?? 0,
      spamScore: pageStatistics.backlinks_spam_score ?? null,
      domainRating: pageStatistics.domain_rating ?? null,
    };
  }, [pageStatistics, hasData]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#0C152B',
          borderRadius: '12px',
          maxHeight: '90vh',
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AnalyticsIcon sx={{ color: '#66CCFF' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            DataForSEO Analysis: {domain}
          </Typography>
        </Box>
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

      <DialogContent sx={{ mt: 2, maxHeight: 'calc(90vh - 140px)', overflowY: 'auto' }}>
        {!hasData ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <AnalyticsIcon sx={{ color: '#66CCFF', fontSize: 48, mb: 2 }} />
            <Typography variant="h6" sx={{ color: '#FFFFFF', mb: 2, fontWeight: 600 }}>
              No DataForSEO Data Available
            </Typography>
            <Typography sx={{ color: '#FFFFFF', opacity: 0.7 }}>
              This domain doesn't have DataForSEO analysis yet.
              <br />
              Use the "Trigger Bulk Analysis" button to analyze domains.
            </Typography>
          </Box>
        ) : (
          <>
            {/* Summary Cards */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '12px',
                    borderLeft: '4px solid #3b82f6',
                    height: '100%',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <LinkIcon sx={{ color: '#3b82f6', fontSize: 24 }} />
                    <Typography
                      variant="overline"
                      sx={{ color: 'rgba(255, 255, 255, 0.6)', fontWeight: 600, textTransform: 'uppercase' }}
                    >
                      Total Backlinks
                    </Typography>
                  </Box>
                  <Typography
                    variant="h3"
                    sx={{
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontFamily: 'monospace',
                    }}
                  >
                    {summary?.backlinks.toLocaleString() || 0}
                  </Typography>
                </Paper>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '12px',
                    borderLeft: '4px solid #10b981',
                    height: '100%',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <DomainIcon sx={{ color: '#10b981', fontSize: 24 }} />
                    <Typography
                      variant="overline"
                      sx={{ color: 'rgba(255, 255, 255, 0.6)', fontWeight: 600, textTransform: 'uppercase' }}
                    >
                      Referring Domains
                    </Typography>
                  </Box>
                  <Typography
                    variant="h3"
                    sx={{
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontFamily: 'monospace',
                    }}
                  >
                    {summary?.referringDomains.toLocaleString() || 0}
                  </Typography>
                </Paper>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '12px',
                    borderLeft: '4px solid #f59e0b',
                    height: '100%',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <LanguageIcon sx={{ color: '#f59e0b', fontSize: 24 }} />
                    <Typography
                      variant="overline"
                      sx={{ color: 'rgba(255, 255, 255, 0.6)', fontWeight: 600, textTransform: 'uppercase' }}
                    >
                      Referring Pages
                    </Typography>
                  </Box>
                  <Typography
                    variant="h3"
                    sx={{
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontFamily: 'monospace',
                    }}
                  >
                    {summary?.referringPages.toLocaleString() || 0}
                  </Typography>
                </Paper>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Paper
                  sx={{
                    p: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '12px',
                    borderLeft: '4px solid #ef4444',
                    height: '100%',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <WarningIcon sx={{ color: '#ef4444', fontSize: 24 }} />
                    <Typography
                      variant="overline"
                      sx={{ color: 'rgba(255, 255, 255, 0.6)', fontWeight: 600, textTransform: 'uppercase' }}
                    >
                      Spam Score
                    </Typography>
                  </Box>
                  <Typography
                    variant="h3"
                    sx={{
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontFamily: 'monospace',
                    }}
                  >
                    {summary?.spamScore !== null && summary?.spamScore !== undefined
                      ? `${summary.spamScore}%`
                      : 'N/A'}
                  </Typography>
                </Paper>
              </Grid>

              {summary?.domainRating !== null && summary?.domainRating !== undefined && (
                <Grid item xs={12} sm={6} md={3}>
                  <Paper
                    sx={{
                      p: 3,
                      bgcolor: 'rgba(255, 255, 255, 0.05)',
                      borderRadius: '12px',
                      borderLeft: '4px solid #8b5cf6',
                      height: '100%',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <TrendingUpIcon sx={{ color: '#8b5cf6', fontSize: 24 }} />
                      <Typography
                        variant="overline"
                        sx={{ color: 'rgba(255, 255, 255, 0.6)', fontWeight: 600, textTransform: 'uppercase' }}
                      >
                        Domain Rating
                      </Typography>
                    </Box>
                    <Typography
                      variant="h3"
                      sx={{
                        color: '#FFFFFF',
                        fontWeight: 700,
                        fontFamily: 'monospace',
                      }}
                    >
                      {summary.domainRating}
                    </Typography>
                  </Paper>
                </Grid>
              )}
            </Grid>

            {/* Charts Section */}
            {(chartData.tldData.length > 0 || chartData.countryData.length > 0) && (
              <Grid container spacing={3} sx={{ mb: 4 }}>
                {/* TLD Distribution Pie Chart */}
                {chartData.tldData.length > 0 && (
                  <Grid item xs={12} md={6}>
                    <Paper
                      sx={{
                        p: 3,
                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '12px',
                        height: '100%',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <LanguageIcon sx={{ color: '#66CCFF', fontSize: 20 }} />
                        <Typography variant="h6" sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                          TLD Distribution
                        </Typography>
                      </Box>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={chartData.tldData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey="value"
                          >
                            {chartData.tldData.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={CHART_COLORS[index % CHART_COLORS.length]}
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1a1a2e',
                              border: '1px solid rgba(102, 204, 255, 0.3)',
                              borderRadius: '8px',
                              color: '#FFFFFF',
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </Paper>
                  </Grid>
                )}

                {/* Country Breakdown Bar Chart */}
                {chartData.countryData.length > 0 && (
                  <Grid item xs={12} md={6}>
                    <Paper
                      sx={{
                        p: 3,
                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '12px',
                        height: '100%',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <PublicIcon sx={{ color: '#66CCFF', fontSize: 20 }} />
                        <Typography variant="h6" sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                          Country Breakdown
                        </Typography>
                      </Box>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={chartData.countryData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                          <XAxis
                            dataKey="name"
                            stroke="#FFFFFF"
                            style={{ fontSize: '12px' }}
                          />
                          <YAxis stroke="#FFFFFF" style={{ fontSize: '12px' }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1a1a2e',
                              border: '1px solid rgba(102, 204, 255, 0.3)',
                              borderRadius: '8px',
                              color: '#FFFFFF',
                            }}
                          />
                          <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </Paper>
                  </Grid>
                )}
              </Grid>
            )}

            <Divider sx={{ my: 3, borderColor: 'rgba(255, 255, 255, 0.1)' }} />

            {/* Raw Data Section - Collapsible */}
            <Paper
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '12px',
                overflow: 'hidden',
              }}
            >
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  p: 2,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.08)' },
                }}
                onClick={() => setRawDataExpanded(!rawDataExpanded)}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CodeIcon sx={{ color: '#66CCFF', fontSize: 20 }} />
                  <Typography variant="h6" sx={{ color: '#FFFFFF', fontWeight: 600 }}>
                    Raw Data (Interactive JSON Viewer)
                  </Typography>
                </Box>
                {rawDataExpanded ? (
                  <ExpandLessIcon sx={{ color: '#66CCFF' }} />
                ) : (
                  <ExpandMoreIcon sx={{ color: '#66CCFF' }} />
                )}
              </Box>
              <Collapse in={rawDataExpanded}>
                <Box
                  sx={{
                    p: 3,
                    bgcolor: 'rgba(0, 0, 0, 0.4)',
                    borderTop: '1px solid rgba(102, 204, 255, 0.2)',
                    maxHeight: '50vh',
                    overflow: 'auto',
                  }}
                >
                  <JSONViewer data={pageStatistics} />
                </Box>
                <Box sx={{ p: 2, borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip
                      label="Click to expand/collapse sections"
                      size="small"
                      sx={{
                        bgcolor: 'rgba(102, 204, 255, 0.1)',
                        color: '#66CCFF',
                        fontSize: '0.75rem',
                      }}
                    />
                    <Chip
                      label="Numbers in green"
                      size="small"
                      sx={{
                        bgcolor: 'rgba(76, 175, 80, 0.1)',
                        color: '#4CAF50',
                        fontSize: '0.75rem',
                      }}
                    />
                    <Chip
                      label="Strings in orange"
                      size="small"
                      sx={{
                        bgcolor: 'rgba(255, 152, 0, 0.1)',
                        color: '#FF9800',
                        fontSize: '0.75rem',
                      }}
                    />
                    <Chip
                      label="Booleans in blue"
                      size="small"
                      sx={{
                        bgcolor: 'rgba(33, 150, 243, 0.1)',
                        color: '#2196F3',
                        fontSize: '0.75rem',
                      }}
                    />
                  </Box>
                </Box>
              </Collapse>
            </Paper>
          </>
        )}
      </DialogContent>

      <DialogActions
        sx={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          p: 2,
        }}
      >
        <Button
          onClick={onClose}
          sx={{
            color: '#FFFFFF',
            textTransform: 'none',
            '&:hover': {
              bgcolor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DataForSEOPopup;







