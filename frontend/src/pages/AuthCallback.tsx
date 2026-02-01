import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { Box, CircularProgress, Typography, Alert, Button } from '@mui/material';

const AuthCallback: React.FC = () => {
    const navigate = useNavigate();
    const [status, setStatus] = useState<string>('Processing authentication...');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const handleCallback = async () => {
            // 1. Check for errors in the URL immediately
            const params = new URLSearchParams(window.location.search);
            const hashParams = new URLSearchParams(window.location.hash.replace('#', '?'));

            const errorDescription = params.get('error_description') || hashParams.get('error_description');
            const errorMsg = params.get('error') || hashParams.get('error');

            if (errorMsg || errorDescription) {
                console.error('Auth Error from URL:', errorMsg, errorDescription);
                setError(errorDescription || errorMsg || 'Authentication failed');
                setStatus('Failed');
                return;
            }

            try {
                // 2. Check if we already have a session
                const { data: { session }, error: sessionError } = await supabase.auth.getSession();

                if (sessionError) {
                    console.error('Session Error:', sessionError);
                    setError(sessionError.message);
                    setStatus('Failed');
                } else if (session) {
                    // Success!
                    console.log('Session found, redirecting...');
                    navigate('/');
                } else {
                    // 3. Setup listener for the asynchronous exchange
                    setStatus('Waiting for session exchange...');
                    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
                        console.log('Auth Event:', event);
                        if (event === 'SIGNED_IN' && session) {
                            navigate('/');
                        }
                        if (event === 'SIGNED_OUT') {
                            // This might happen if exchange fails silently?
                            // Keep waiting or potential timeout
                        }
                    });

                    // 4. Fallback Timeout
                    setTimeout(() => {
                        if (!error) {
                            // If we are still waiting after 10 seconds, something is wrong
                            // But don't force fail if the user is just on slow network, 
                            // allow them to try again manually.
                            setError('Authentication request timed out. Please try again.');
                            setStatus('Timeout');
                        }
                    }, 10000);
                }
            } catch (e: any) {
                console.error('Exception:', e);
                setError(e.message || 'An unexpected error occurred');
                setStatus('Error');
            }
        };

        handleCallback();
    }, [navigate]);

    return (
        <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100vh',
            bgcolor: '#0C152B',
            color: 'white'
        }}>
            {error ? (
                <Box sx={{ p: 4, textAlign: 'center', maxWidth: 400 }}>
                    <Alert severity="error" sx={{ mb: 3 }}>
                        {error}
                    </Alert>
                    <Typography variant="body2" sx={{ mb: 3, opacity: 0.7 }}>
                        Please check your network connection and try again.
                    </Typography>
                    <Button variant="contained" onClick={() => navigate('/login')}>
                        Back to Login
                    </Button>
                </Box>
            ) : (
                <>
                    <CircularProgress sx={{ mb: 3 }} />
                    <Typography variant="h6">
                        {status}
                    </Typography>
                </>
            )}
        </Box>
    );
};

export default AuthCallback;
