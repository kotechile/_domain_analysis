import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
} from '@mui/material';
import {
  Language as LanguageIcon,
} from '@mui/icons-material';

const Header: React.FC = () => {
  const navigate = useNavigate();

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{
        backgroundColor: '#0C152B',
      }}
    >
      <Toolbar sx={{ px: { xs: 3, sm: 4 }, minHeight: 64, justifyContent: 'space-between' }}>
        {/* Logo and Title */}
        <Box 
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer',
          }}
          onClick={() => navigate('/')}
        >
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 1,
              bgcolor: '#66CCFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mr: 1.5,
            }}
          >
            <LanguageIcon sx={{ fontSize: 20, color: '#0C152B' }} />
          </Box>
          <Typography 
            variant="h6" 
            component="div" 
            sx={{ 
              fontWeight: 600,
              fontSize: '1.25rem',
              color: '#FFFFFF',
            }}
          >
            DomainScope
            <Box component="span" sx={{ color: '#66CCFF', ml: 0.5 }}>
              AI
            </Box>
          </Typography>
        </Box>

        {/* Right side navigation */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <Button
            onClick={() => navigate('/marketplace')}
            sx={{
              color: '#FFFFFF',
              textTransform: 'none',
              fontSize: '0.9375rem',
              fontWeight: 400,
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
              },
            }}
          >
            Marketplace
          </Button>
          <Button
            onClick={() => navigate('/reports')}
            variant="contained"
            sx={{
              backgroundColor: '#2962FF',
              color: '#FFFFFF',
              textTransform: 'none',
              fontSize: '0.9375rem',
              fontWeight: 500,
              borderRadius: '20px',
              px: 2.5,
              py: 0.75,
              '&:hover': {
                backgroundColor: '#1E4ED8',
              },
            }}
          >
            Analysis History
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
