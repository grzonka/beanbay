import { useThemeMode } from '@/theme/ThemeContext';
import {
  Add as AddIcon,
  LocalCafe as BeansIcon,
  CoffeeMaker as BrewersIcon,
  Coffee as BrewsIcon,
  ChevronLeft as ChevronLeftIcon,
  Star as CuppingsIcon,
  DarkMode as DarkModeIcon,
  Dashboard as DashboardIcon,
  BlenderOutlined as GrindersIcon,
  LightMode as LightModeIcon,
  Menu as MenuIcon,
  AutoFixHigh as OptimizeIcon,
  FilterAlt as PapersIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  Tune as SetupsIcon,
  WaterDrop as WatersIcon,
} from '@mui/icons-material';
import {
  AppBar,
  Box,
  Drawer,
  Fab,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  ListSubheader,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { useState } from 'react';
import {
  Outlet,
  Link as RouterLink,
  useLocation,
  useNavigate,
} from 'react-router';

const DRAWER_WIDTH = 240;
const DRAWER_COLLAPSED = 64;

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

const navGroups: { label: string; items: NavItem[] }[] = [
  {
    label: 'Core',
    items: [
      { label: 'Dashboard', path: '/', icon: <DashboardIcon /> },
      { label: 'Beans', path: '/beans', icon: <BeansIcon /> },
      { label: 'Brews', path: '/brews', icon: <BrewsIcon /> },
      { label: 'Optimize', path: '/optimize', icon: <OptimizeIcon /> },
    ],
  },
  {
    label: 'Equipment',
    items: [
      {
        label: 'Grinders',
        path: '/equipment/grinders',
        icon: <GrindersIcon />,
      },
      { label: 'Brewers', path: '/equipment/brewers', icon: <BrewersIcon /> },
      { label: 'Papers', path: '/equipment/papers', icon: <PapersIcon /> },
      { label: 'Waters', path: '/equipment/waters', icon: <WatersIcon /> },
      { label: 'Brew Setups', path: '/brew-setups', icon: <SetupsIcon /> },
    ],
  },
  {
    label: 'Evaluation',
    items: [{ label: 'Cuppings', path: '/cuppings', icon: <CuppingsIcon /> }],
  },
  {
    label: 'Manage',
    items: [
      { label: 'People', path: '/people', icon: <PeopleIcon /> },
      { label: 'Lookups', path: '/settings/lookups', icon: <SettingsIcon /> },
    ],
  },
];

export default function AppLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { mode, toggleTheme } = useThemeMode();

  const drawerWidth = isMobile
    ? DRAWER_WIDTH
    : collapsed
      ? DRAWER_COLLAPSED
      : DRAWER_WIDTH;

  const drawerContent = (
    <Box sx={{ overflow: 'auto', mt: isMobile ? 0 : 8 }}>
      {!isMobile && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', p: 1 }}>
          <IconButton onClick={() => setCollapsed(!collapsed)} size="small">
            <ChevronLeftIcon
              sx={{
                transform: collapsed ? 'rotate(180deg)' : 'none',
                transition: '0.2s',
              }}
            />
          </IconButton>
        </Box>
      )}
      {navGroups.map((group) => (
        <List
          key={group.label}
          subheader={
            !collapsed ? (
              <ListSubheader
                sx={{
                  bgcolor: 'transparent',
                  lineHeight: '32px',
                  fontSize: 11,
                  letterSpacing: 1,
                  textTransform: 'uppercase',
                }}
              >
                {group.label}
              </ListSubheader>
            ) : undefined
          }
        >
          {group.items.map((item) => {
            const isActive =
              item.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.path);
            return (
              <ListItemButton
                key={item.path}
                component={RouterLink}
                to={item.path}
                selected={isActive}
                onClick={() => isMobile && setMobileOpen(false)}
                sx={{ minHeight: 44, px: collapsed ? 2.5 : 2 }}
              >
                <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40 }}>
                  {item.icon}
                </ListItemIcon>
                {!collapsed && <ListItemText primary={item.label} />}
              </ListItemButton>
            );
          })}
        </List>
      ))}
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        color="default"
        elevation={0}
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Toolbar>
          {isMobile && (
            <IconButton
              edge="start"
              onClick={() => setMobileOpen(!mobileOpen)}
              sx={{ mr: 1 }}
            >
              <MenuIcon />
            </IconButton>
          )}
          <Typography
            variant="h6"
            noWrap
            component={RouterLink}
            to="/"
            sx={{
              flexGrow: 1,
              textDecoration: 'none',
              color: 'text.primary',
              fontFamily: '"DM Serif Display", serif',
            }}
          >
            BeanBay
          </Typography>
          <Tooltip
            title={mode === 'dark' ? 'Switch to light' : 'Switch to dark'}
          >
            <IconButton onClick={toggleTheme}>
              {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {isMobile ? (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH } }}
        >
          {drawerContent}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              transition: theme.transitions.create('width', { duration: 200 }),
              overflowX: 'hidden',
            },
          }}
        >
          {drawerContent}
        </Drawer>
      )}

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, sm: 3 },
          mt: 8,
          pb: { xs: 10, sm: 3 },
          width: { md: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Outlet />
      </Box>

      <Fab
        color="primary"
        variant="extended"
        onClick={() => navigate('/brews/new')}
        sx={{
          position: 'fixed',
          bottom: { xs: 16, sm: 24 },
          right: { xs: 16, sm: 24 },
        }}
      >
        <AddIcon sx={{ mr: 1 }} />
        Log a Brew
      </Fab>
    </Box>
  );
}
