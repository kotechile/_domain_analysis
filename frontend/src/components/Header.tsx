import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Chip,
} from '@mui/material';
import {
  Analytics as AnalyticsIcon,
  List as ListIcon,
  Home as HomeIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    handleMenuClose();
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        {/* Logo and Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', mr: 4 }}>
          <AnalyticsIcon sx={{ mr: 1 }} />
          <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
            Domain Analysis
          </Typography>
          <Chip
            label="v1.0"
            size="small"
            color="secondary"
            sx={{ ml: 2, fontSize: '0.75rem' }}
          />
        </Box>

        {/* Navigation Buttons */}
        <Box sx={{ display: 'flex', gap: 1, flexGrow: 1 }}>
          <Button
            color="inherit"
            startIcon={<HomeIcon />}
            onClick={() => navigate('/')}
            sx={{
              backgroundColor: isActive('/') ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            }}
          >
            Analysis
          </Button>
          <Button
            color="inherit"
            startIcon={<ListIcon />}
            onClick={() => navigate('/reports')}
            sx={{
              backgroundColor: isActive('/reports') ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            }}
          >
            Reports
          </Button>
        </Box>

        {/* Right side menu */}
        <Box>
          <IconButton
            color="inherit"
            onClick={handleMenuOpen}
            aria-label="more options"
          >
            <MoreVertIcon />
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'right',
            }}
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
          >
            <MenuItem onClick={() => handleNavigation('/')}>
              <HomeIcon sx={{ mr: 1 }} />
              New Analysis
            </MenuItem>
            <MenuItem onClick={() => handleNavigation('/reports')}>
              <ListIcon sx={{ mr: 1 }} />
              View Reports
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
