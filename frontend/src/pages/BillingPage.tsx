import React, { useState } from 'react';
import {
    Box,
    Container,
    Typography,
    Card,
    CardContent,
    Grid,
    Button,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Chip,
    Stack,
    CircularProgress,
    Tabs,
    Tab,
    Alert,
    Divider,
} from '@mui/material';
import {
    AccountBalanceWallet as WalletIcon,
    Receipt as ReceiptIcon,
    ShoppingBag as ShoppingIcon,
    History as HistoryIcon,
    ArrowUpward as UpIcon,
    ArrowDownward as DownIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApi, TransactionResponse } from '../services/api';
import Header from '../components/Header';

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;
    return (
        <div role="tabpanel" hidden={value !== index} {...other}>
            {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
        </div>
    );
}

const BillingPage: React.FC = () => {
    const api = useApi();
    const queryClient = useQueryClient();
    const [tabValue, setTabValue] = useState(0);

    // Fetch Balance
    const { data: balanceData, isLoading: balanceLoading } = useQuery({
        queryKey: ['credits-balance'],
        queryFn: () => api.getBalance(),
    });

    // Fetch Payments History
    const { data: payments, isLoading: paymentsLoading } = useQuery({
        queryKey: ['payments-history'],
        queryFn: () => api.getPaymentHistory(50),
    });

    // Fetch Full Transaction Ledger
    const { data: transactions, isLoading: transactionsLoading } = useQuery({
        queryKey: ['credits-transactions'],
        queryFn: () => api.getTransactions(50),
    });

    // Mock Purchase Mutation
    const purchaseMutation = useMutation({
        mutationFn: (amount: number) => api.purchaseCredits(amount, `Purchased ${amount} credits via Dashboard`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['credits-balance'] });
            queryClient.invalidateQueries({ queryKey: ['payments-history'] });
            queryClient.invalidateQueries({ queryKey: ['credits-transactions'] });
        },
    });

    const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
        setTabValue(newValue);
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const TransactionTable = ({ data }: { data: TransactionResponse[] }) => (
        <TableContainer component={Paper} elevation={0} variant="outlined" sx={{ borderRadius: 2 }}>
            <Table>
                <TableHead sx={{ bgcolor: 'action.hover' }}>
                    <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                        <TableCell sx={{ fontWeight: 600 }} align="right">Amount (Credits)</TableCell>
                        <TableCell sx={{ fontWeight: 600 }} align="right">Amount (USD)</TableCell>
                        <TableCell sx={{ fontWeight: 600 }} align="right">New Balance</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data.map((row) => (
                        <TableRow key={row.id} hover>
                            <TableCell variant="body">{formatDate(row.created_at)}</TableCell>
                            <TableCell>
                                <Typography variant="body2" fontWeight={500}>{row.description}</Typography>
                                <Typography variant="caption" color="text.secondary" display="block">
                                    Ref: {row.reference_id || 'N/A'}
                                </Typography>
                            </TableCell>
                            <TableCell>
                                <Chip
                                    label={row.transaction_type}
                                    size="small"
                                    color={row.amount > 0 ? 'success' : 'default'}
                                    variant="outlined"
                                    sx={{ textTransform: 'capitalize', fontWeight: 600 }}
                                />
                            </TableCell>
                            <TableCell align="right">
                                <Stack direction="row" spacing={0.5} alignItems="center" justifyContent="flex-end">
                                    {row.amount > 0 ? <UpIcon color="success" fontSize="inherit" /> : <DownIcon color="error" fontSize="inherit" />}
                                    <Typography variant="body2" fontWeight={600} color={row.amount > 0 ? 'success.main' : 'error.main'}>
                                        {row.amount > 0 ? '+' : ''}{row.amount.toLocaleString()}
                                    </Typography>
                                </Stack>
                            </TableCell>
                            <TableCell align="right">
                                <Typography variant="body2" fontWeight={500}>
                                    {row.dollar_amount !== 0 ? (
                                        <Box component="span" color={row.dollar_amount > 0 ? 'success.main' : 'error.main'}>
                                            {row.dollar_amount > 0 ? '+' : ''}${Math.abs(row.dollar_amount).toFixed(2)}
                                        </Box>
                                    ) : '—'}
                                </Typography>
                            </TableCell>
                            <TableCell align="right">
                                <Typography variant="body2" fontWeight={600}>
                                    {row.balance_after.toLocaleString()}
                                </Typography>
                            </TableCell>
                        </TableRow>
                    ))}
                    {data.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                                <Typography variant="body2" color="text.secondary">No transactions found.</Typography>
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </TableContainer>
    );

    return (
        <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
            <Header />
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Box sx={{ mb: 4 }}>
                    <Typography variant="h4" fontWeight={700} gutterBottom>
                        Billing & Credits
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Manage your credits, view payment history, and track usage.
                    </Typography>
                </Box>

                <Grid container spacing={3} sx={{ mb: 4 }}>
                    <Grid item xs={12} md={4}>
                        <Card sx={{ height: '100%', borderRadius: 3, bgcolor: 'primary.main', color: 'primary.contrastText' }}>
                            <CardContent sx={{ p: 4 }}>
                                <Stack spacing={1}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <WalletIcon />
                                        <Typography variant="subtitle2" sx={{ opacity: 0.8 }}>Current Balance</Typography>
                                    </Box>
                                    <Typography variant="h3" fontWeight={800}>
                                        {balanceLoading ? <CircularProgress size={32} color="inherit" /> : balanceData?.balance.toLocaleString()}
                                    </Typography>
                                    <Typography variant="body2" sx={{ opacity: 0.8 }}>
                                        Available Credits
                                    </Typography>
                                </Stack>
                            </CardContent>
                        </Card>
                    </Grid>

                    <Grid item xs={12} md={8}>
                        <Card sx={{ height: '100%', borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
                            <CardContent sx={{ p: 3 }}>
                                <Typography variant="h6" fontWeight={700} gutterBottom>Quick Top-up</Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                                    Add more credits to your account instantly. One credit is approximately $0.001.
                                </Typography>
                                <Stack direction="row" spacing={2}>
                                    {[100, 500, 1000, 5000].map((amount) => (
                                        <Button
                                            key={amount}
                                            variant="outlined"
                                            onClick={() => purchaseMutation.mutate(amount)}
                                            disabled={purchaseMutation.isPending}
                                            sx={{ borderRadius: 2, px: 3 }}
                                        >
                                            +{amount}
                                        </Button>
                                    ))}
                                </Stack>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>

                <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
                        <Tabs value={tabValue} onChange={handleTabChange}>
                            <Tab icon={<ReceiptIcon />} iconPosition="start" label="Payment History" />
                            <Tab icon={<HistoryIcon />} iconPosition="start" label="Usage Ledger" />
                        </Tabs>
                    </Box>

                    <CardContent sx={{ pt: 0 }}>
                        <TabPanel value={tabValue} index={0}>
                            <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>
                                Payment & Top-up History
                            </Typography>
                            {paymentsLoading ? (
                                <Box sx={{ py: 4, textAlign: 'center' }}><CircularProgress /></Box>
                            ) : (
                                <TransactionTable data={payments || []} />
                            )}
                        </TabPanel>

                        <TabPanel value={tabValue} index={1}>
                            <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>
                                Full Credit Ledger
                            </Typography>
                            <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
                                This ledger shows every credit deduction (scans, refreshes) and additions (top-ups, resets).
                            </Alert>
                            {transactionsLoading ? (
                                <Box sx={{ py: 4, textAlign: 'center' }}><CircularProgress /></Box>
                            ) : (
                                <TransactionTable data={transactions || []} />
                            )}
                        </TabPanel>
                    </CardContent>
                </Card>
            </Container>
        </Box>
    );
};

export default BillingPage;
