import React, { useEffect, useState } from 'react';
import {
  AppBar,
  Box,
  Toolbar,
  Typography,
  Button,
  Container,
  Stack,
  Avatar,
  Menu,
  MenuItem,
  IconButton
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import {
  Language as LanguageIcon,
} from '@mui/icons-material';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = React.useState<any>(null);
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  React.useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    handleClose();
    navigate('/login');
  };

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const isActive = (path: string) => location.pathname === path;
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
          {/* Auth Menu */}
          <Box>
            {session ? (
              <>
                <IconButton
                  size="large"
                  aria-label="account of current user"
                  aria-controls="menu-appbar"
                  aria-haspopup="true"
                  onClick={handleMenu}
                  color="inherit"
                >
                  <Avatar sx={{ bgcolor: '#2962FF', width: 32, height: 32 }}>
                    {session.user.email?.charAt(0).toUpperCase() || <AccountCircleIcon />}
                  </Avatar>
                </IconButton>
                <Menu
                  id="menu-appbar"
                  anchorEl={anchorEl}
                  anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'right',
                  }}
                  keepMounted
                  transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right',
                  }}
                  open={Boolean(anchorEl)}
                  onClose={handleClose}
                >
                  <MenuItem disabled sx={{ opacity: 1 }}>
                    <Typography variant="caption" color="textSecondary">{session.user.email}</Typography>
                  </MenuItem>
                  <MenuItem onClick={handleLogout}>Logout</MenuItem>
                </Menu>
              </>
            ) : (
              <Button
                color="inherit"
                onClick={() => navigate('/login')}
                sx={{ textTransform: 'none' }}
              >
                Login
              </Button>
            )}
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
