import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Card,
    CardContent,
    Grid,
    Alert,
    CircularProgress,
    useTheme,
    Paper,
    Stack,
    ToggleButtonGroup,
    ToggleButton,
} from '@mui/material';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import { HistoricalData, useApi } from '../services/api';
import {
    TrendingUp as TrendingUpIcon,
    ShowChart as ShowChartIcon,
    Info as InfoIcon,
} from '@mui/icons-material';

interface HistoricalDataChartProps {
    domain: string;
    data?: HistoricalData;
}

const HistoricalDataChart: React.FC<HistoricalDataChartProps> = ({ domain, data: propData }) => {
    const theme = useTheme();
    const api = useApi();
    const [historicalData, setHistoricalData] = useState<HistoricalData | null>(propData || null);
    const [loading, setLoading] = useState(!propData);
    const [error, setError] = useState<string | null>(null);
    const [selectedMetric, setSelectedMetric] = useState<'ranking' | 'traffic'>('ranking');

    useEffect(() => {
        if (!propData) {
            fetchHistoricalData();
        }
    }, [domain, propData]);

    const fetchHistoricalData = async () => {
        try {
            setLoading(true);
            setError(null);
            const fetchedData = await api.getHistoricalData(domain);
            setHistoricalData(fetchedData);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch historical data');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    };

    const formatNumber = (num: number) => {
        if (num >= 1000000) {
            return `${(num / 1000000).toFixed(1)}M`;
        } else if (num >= 1000) {
            return `${(num / 1000).toFixed(1)}K`;
        }
        return num.toFixed(0);
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
                <Stack spacing={2} alignItems="center">
                    <CircularProgress />
                    <Typography color="text.secondary">Loading historical data...</Typography>
                </Stack>
            </Box>
        );
    }

    if (error) {
        return (
            <Alert severity="error" sx={{ borderRadius: 2 }}>
                <Typography variant="h6" gutterBottom>
                    Failed to load historical data
                </Typography>
                <Typography variant="body2">{error}</Typography>
            </Alert>
        );
    }

    if (!historicalData) {
        return (
            <Box sx={{ textAlign: 'center', py: 8 }}>
                <ShowChartIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                    No historical data available
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Historical metrics will be collected during future analysis runs.
                </Typography>
            </Box>
        );
    }

    const hasRankingData =
        historicalData.rank_overview &&
        (historicalData.rank_overview.organic_keywords_count.length > 0 ||
            historicalData.rank_overview.organic_traffic.length > 0);

    const hasTrafficData =
        historicalData.traffic_analytics &&
        (historicalData.traffic_analytics.visits_history.length > 0 ||
            historicalData.traffic_analytics.unique_visitors_history.length > 0);

    if (!hasRankingData && !hasTrafficData) {
        return (
            <Alert severity="info" sx={{ borderRadius: 2 }}>
                No historical data available for this domain. The analysis may not have collected historical data.
            </Alert>
        );
    }

    // Prepare ranking chart data
    const rankingChartData = historicalData.rank_overview
        ? historicalData.rank_overview.organic_keywords_count.map((point, index) => {
            const traffic = historicalData.rank_overview?.organic_traffic[index] || { value: 0 };
            const trafficValue = historicalData.rank_overview?.organic_traffic_value[index] || { value: 0 };

            return {
                date: formatDate(point.date),
                keywords: point.value,
                traffic: traffic.value,
                trafficValue: trafficValue.value,
            };
        })
        : [];

    // Prepare traffic chart data
    const trafficChartData = historicalData.traffic_analytics
        ? historicalData.traffic_analytics.visits_history.map((point, index) => {
            const unique = historicalData.traffic_analytics?.unique_visitors_history[index] || { value: 0 };
            const bounce = historicalData.traffic_analytics?.bounce_rate_history[index] || { value: 0 };

            return {
                date: formatDate(point.date),
                visits: point.value,
                uniqueVisitors: unique.value,
                bounceRate: bounce.value * 100, // Convert to percentage
            };
        })
        : [];

    return (
        <Box>
            {/* Metric Selector */}
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
                <ToggleButtonGroup
                    value={selectedMetric}
                    exclusive
                    onChange={(_, newValue) => newValue && setSelectedMetric(newValue)}
                    sx={{
                        '& .MuiToggleButton-root': {
                            px: 3,
                            py: 1,
                            borderRadius: 2,
                        },
                    }}
                >
                    {hasRankingData && (
                        <ToggleButton value="ranking">
                            <TrendingUpIcon sx={{ mr: 1 }} />
                            SEO Rankings
                        </ToggleButton>
                    )}
                    {hasTrafficData && (
                        <ToggleButton value="traffic">
                            <ShowChartIcon sx={{ mr: 1 }} />
                            Traffic Analytics
                        </ToggleButton>
                    )}
                </ToggleButtonGroup>
            </Box>

            {/* Ranking Charts */}
            {selectedMetric === 'ranking' && hasRankingData && (
                <Grid container spacing={3}>
                    <Grid item xs={12}>
                        <Card variant="outlined" sx={{ borderRadius: 2 }}>
                            <CardContent>
                                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                                    Organic Keywords & Traffic Trends
                                </Typography>
                                <ResponsiveContainer width="100%" height={400}>
                                    <LineChart data={rankingChartData}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke={theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}
                                        />
                                        <XAxis
                                            dataKey="date"
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                        />
                                        <YAxis
                                            yAxisId="left"
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                            tickFormatter={formatNumber}
                                        />
                                        <YAxis
                                            yAxisId="right"
                                            orientation="right"
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                            tickFormatter={formatNumber}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: theme.palette.mode === 'dark' ? '#1a1a2e' : '#ffffff',
                                                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(102, 204, 255, 0.3)' : 'rgba(0, 0, 0, 0.1)'}`,
                                                borderRadius: '8px',
                                                color: theme.palette.text.primary,
                                            }}
                                            formatter={(value: number | undefined) => value !== undefined ? formatNumber(value) : ''}
                                        />
                                        <Legend />
                                        <Line
                                            yAxisId="left"
                                            type="monotone"
                                            dataKey="keywords"
                                            stroke="#3b82f6"
                                            strokeWidth={2}
                                            dot={{ fill: '#3b82f6', r: 4 }}
                                            name="Organic Keywords"
                                        />
                                        <Line
                                            yAxisId="right"
                                            type="monotone"
                                            dataKey="traffic"
                                            stroke="#10b981"
                                            strokeWidth={2}
                                            dot={{ fill: '#10b981', r: 4 }}
                                            name="Organic Traffic"
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>
                    </Grid>

                    <Grid item xs={12}>
                        <Card variant="outlined" sx={{ borderRadius: 2 }}>
                            <CardContent>
                                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                                    Organic Traffic Value
                                </Typography>
                                <ResponsiveContainer width="100%" height={300}>
                                    <LineChart data={rankingChartData}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke={theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}
                                        />
                                        <XAxis
                                            dataKey="date"
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                        />
                                        <YAxis
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                            tickFormatter={(value) => `$${formatNumber(value)}`}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: theme.palette.mode === 'dark' ? '#1a1a2e' : '#ffffff',
                                                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(102, 204, 255, 0.3)' : 'rgba(0, 0, 0, 0.1)'}`,
                                                borderRadius: '8px',
                                                color: theme.palette.text.primary,
                                            }}
                                            formatter={(value: number | undefined) => value !== undefined ? `$${formatNumber(value)}` : ''}
                                        />
                                        <Legend />
                                        <Line
                                            type="monotone"
                                            dataKey="trafficValue"
                                            stroke="#f59e0b"
                                            strokeWidth={2}
                                            dot={{ fill: '#f59e0b', r: 4 }}
                                            name="Traffic Value ($)"
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            )}

            {/* Traffic Charts */}
            {selectedMetric === 'traffic' && hasTrafficData && (
                <Grid container spacing={3}>
                    <Grid item xs={12}>
                        <Card variant="outlined" sx={{ borderRadius: 2 }}>
                            <CardContent>
                                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                                    Website Visits & Unique Visitors
                                </Typography>
                                <ResponsiveContainer width="100%" height={400}>
                                    <LineChart data={trafficChartData}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke={theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}
                                        />
                                        <XAxis
                                            dataKey="date"
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                        />
                                        <YAxis
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                            tickFormatter={formatNumber}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: theme.palette.mode === 'dark' ? '#1a1a2e' : '#ffffff',
                                                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(102, 204, 255, 0.3)' : 'rgba(0, 0, 0, 0.1)'}`,
                                                borderRadius: '8px',
                                                color: theme.palette.text.primary,
                                            }}
                                            formatter={(value: number | undefined) => value !== undefined ? formatNumber(value) : ''}
                                        />
                                        <Legend />
                                        <Line
                                            type="monotone"
                                            dataKey="visits"
                                            stroke="#8b5cf6"
                                            strokeWidth={2}
                                            dot={{ fill: '#8b5cf6', r: 4 }}
                                            name="Total Visits"
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="uniqueVisitors"
                                            stroke="#ec4899"
                                            strokeWidth={2}
                                            dot={{ fill: '#ec4899', r: 4 }}
                                            name="Unique Visitors"
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>
                    </Grid>

                    <Grid item xs={12}>
                        <Card variant="outlined" sx={{ borderRadius: 2 }}>
                            <CardContent>
                                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                                    Bounce Rate %
                                </Typography>
                                <ResponsiveContainer width="100%" height={300}>
                                    <LineChart data={trafficChartData}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke={theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}
                                        />
                                        <XAxis
                                            dataKey="date"
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                        />
                                        <YAxis
                                            stroke={theme.palette.text.secondary}
                                            style={{ fontSize: '12px' }}
                                            tickFormatter={(value) => `${value.toFixed(0)}%`}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: theme.palette.mode === 'dark' ? '#1a1a2e' : '#ffffff',
                                                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(102, 204, 255, 0.3)' : 'rgba(0, 0, 0, 0.1)'}`,
                                                borderRadius: '8px',
                                                color: theme.palette.text.primary,
                                            }}
                                            formatter={(value: number | undefined) => value !== undefined ? `${value.toFixed(1)}%` : ''}
                                        />
                                        <Legend />
                                        <Line
                                            type="monotone"
                                            dataKey="bounceRate"
                                            stroke="#ef4444"
                                            strokeWidth={2}
                                            dot={{ fill: '#ef4444', r: 4 }}
                                            name="Bounce Rate"
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            )}

            {/* Info Card */}
            <Alert severity="info" sx={{ mt: 3, borderRadius: 2 }}>
                <Typography variant="body2">
                    <strong>Data Source:</strong> Historical data is collected from DataForSEO's ranking and traffic analytics APIs. Metrics are updated during each domain analysis run.
                </Typography>
            </Alert>
        </Box>
    );
};

export default HistoricalDataChart;
