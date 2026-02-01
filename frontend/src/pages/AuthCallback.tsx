import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { Box, CircularProgress, Typography } from '@mui/material';

const AuthCallback: React.FC = () => {
    const navigate = useNavigate();

    useEffect(() => {
        // Supabase handles the session exchange automatically when the component mounts 
        // and the URL contains error/access_token/refresh_token...
        // We just need to wait for the session to be established.

        const handleCallback = async () => {
            try {
                const { data: { session }, error } = await supabase.auth.getSession();

                if (error) {
                    console.error('Error during auth callback:', error);
                    navigate('/login'); // Redirect back to login on error
                } else if (session) {
                    navigate('/'); // Redirect to dashboard on success
                } else {
                    // Wait a bit, sometimes it takes a moment for the client to parse the hash
                    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
                        if (event === 'SIGNED_IN' && session) {
                            navigate('/');
                        }
                    });

                    // Cleanup subscription? Not strictly necessary as we navigate away.
                }
            } catch (e) {
                console.error('Exception during auth callback:', e);
                navigate('/login');
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
            height: '100vh'
        }}>
            <CircularProgress />
            <Typography variant="h6" sx={{ mt: 2 }}>
                Completing sign in...
            </Typography>
        </Box>
    );
};

export default AuthCallback;
