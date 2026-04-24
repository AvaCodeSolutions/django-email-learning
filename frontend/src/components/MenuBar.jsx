import { useState, useEffect } from 'react'
import { AppBar, Chip, Drawer, Box, Typography, MenuList, MenuItem, ListItemIcon, ListItemText, Tooltip, Link, Select, Stack, Collapse } from '@mui/material'
import IconButton from '@mui/material/IconButton';
import SchoolOutlinedIcon from '@mui/icons-material/SchoolOutlined';
import PeopleOutlinedIcon from '@mui/icons-material/PeopleOutlined';
import DoneIcon from '@mui/icons-material/Done';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import VpnKeyOutlinedIcon from '@mui/icons-material/VpnKeyOutlined';
import CorporateFareOutlinedIcon from '@mui/icons-material/CorporateFareOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import MenuIcon from '@mui/icons-material/Menu';
import logoHorizontalLightUrl from '../assets/logo-h-light.png'
import logoHorizontalDarkUrl from '../assets/logo-h-dark.png'
import logoVerticalLightUrl from '../assets/logo-v-light.png'
import logoVerticalDarkUrl from '../assets/logo-v-dark.png'
import { getCookie } from '../utils.js';
import { useTheme, useMediaQuery } from "@mui/material";
import ThemeSwitcher from './ThemeSwitcher.jsx';
import { useAppContext } from '../render.jsx';


function OrganizationsSelect({organizations, activeOrganizationId, changeOrganizationCallback, sx}) {

    return (
        <Select
            value={activeOrganizationId || ""}
            onChange={(e) => changeOrganizationCallback(e.target.value)}
            displayEmpty
            inputProps={{ 'aria-label': 'Select organization' }}
            sx={{
                ml: 1,
                fontSize: 16,
                '& .MuiSelect-select': {
                    paddingTop: '8px',
                    paddingBottom: '8px',
                },
                '& .MuiSvgIcon-root': {
                    top: 'calc(50% - 12px)',
                },
                ...sx
            }}
        >
            {organizations.map((org) => (
                <MenuItem key={org.id} value={org.id}>
                    {org.name}
                </MenuItem>
            ))}
        </Select>
    )
}

function MenuBar({activeOrganizationId, changeOrganizationCallback, showOrganizationSwitcher, drawerWidth}) {
    const [menuOpen, setMenuOpen] = useState(false)
    const [organizations, setOrganizations] = useState([])
    const [deliverContentsJobStatus, setDeliverContentsJobStatus] = useState(null)
    const { localeMessages, isPlatformAdmin, isOrganizationAdmin, direction, apiBaseUrl, platformBaseUrl, sidebarCustomComponent, customLogo } = useAppContext();

    const theme = useTheme();
    const isMdUpScreen = useMediaQuery(theme.breakpoints.up('md'));

    const drawerVariant = isMdUpScreen ? "permanent" : "temporary";
    const currentPath = typeof window !== 'undefined' ? window.location.pathname.replace(/\/+$/, '') || '/' : '/';
    const [settingsOpen, setSettingsOpen] = useState(() => /\/settings(\/|$)/.test(currentPath));
    let logoHorizontalUrl, logoVerticalUrl;
    if (customLogo) {
        logoHorizontalUrl = theme.palette.mode === 'light' ? (customLogo.horizontalLight ? customLogo.horizontalLight : customLogo.horizontalDark) : (customLogo.horizontalDark ? customLogo.horizontalDark : customLogo.horizontalLight);
        logoVerticalUrl = theme.palette.mode === 'light' ? (customLogo.verticalLight ? customLogo.verticalLight : customLogo.verticalDark) : (customLogo.verticalDark ? customLogo.verticalDark : customLogo.verticalLight);
    }
    if (!logoHorizontalUrl) {
        logoHorizontalUrl = theme.palette.mode === 'light' ? logoHorizontalLightUrl : logoHorizontalDarkUrl;
    }
    if (!logoVerticalUrl) {
        logoVerticalUrl = theme.palette.mode === 'light' ? logoVerticalLightUrl : logoVerticalDarkUrl;
    }

    const jobsStatusMap = {
        healthy: {
            icon: <DoneIcon fontSize="small" />,
            paletteKey: 'healthy',
        },
        warning: {
            icon: <WarningIcon fontSize="small" />,
            paletteKey: 'warning',
        },
        critical: {
            icon: <ErrorIcon fontSize="small" />,
            paletteKey: 'critical',
        },
    };

    useEffect(() => {
        fetch(apiBaseUrl + '/status/jobs/', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
        .then(data => {
            setDeliverContentsJobStatus(data.jobs.deliver_contents);
        })
        .catch(error => {
            console.error('Error fetching job status:', error);
        });

        if (!showOrganizationSwitcher) {
            return;
        }
        fetch(apiBaseUrl + '/organizations/', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
        .then(data => {
            setOrganizations(data.organizations);
        })
        .catch(error => {
            console.error('Error fetching organizations:', error);
        });
    }, []);

    let pages = []

    if (isOrganizationAdmin) {
        pages.push(
            { name: localeMessages["organizations"], icon: <CorporateFareOutlinedIcon fontSize="small" />, href:  platformBaseUrl + '/organizations/'},
        );
    }

    pages.push({ name: localeMessages["course_management"], icon: <SchoolOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/courses/' });
    if (isOrganizationAdmin || isPlatformAdmin) {
        pages.push({ name: localeMessages["learners"], icon: <PeopleOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/learners/' });
    }
    // pages.push({ name: 'Analytics', icon: <BarChartIcon fontSize="small" />, href: platformBaseUrl + '/analytics/' });
    let settingsPages = []
    if (isPlatformAdmin) {
        settingsPages.push({ name: localeMessages["api_keys"], icon: <VpnKeyOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/settings/api_keys' });
    }


    const toggleMenuDrawer = (newOpen) => () => {
        setMenuOpen(newOpen);
    };

    const isActivePage = (href) => {
        if (typeof window === 'undefined') {
            return false;
        }
        const pagePath = new URL(href, window.location.origin).pathname.replace(/\/+$/, '') || '/';
        return currentPath === pagePath || (pagePath !== '/' && currentPath.startsWith(`${pagePath}/`));
    };

    const isSettingsSectionActive = settingsPages.some((page) => isActivePage(page.href));

        const healthStatus = deliverContentsJobStatus?.job_health_status || 'healthy';
        const statusConfig = jobsStatusMap[healthStatus] || jobsStatusMap.healthy;
        const executionTime = deliverContentsJobStatus?.last_execution_started_at
            ? new Date(deliverContentsJobStatus.last_execution_started_at).toLocaleString()
            : null;


    return (
        <Box component="nav"sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <AppBar sx={{boxShadow: 0, backgroundColor: 'background.nav', borderBottom: {xs: '1px solid'}, borderColor: {xs: 'border.main', md: 'none'} }}>
            <Box sx={{ my: 1, ml: 5, height: { xs: "57px", md: "30px" }, display: 'flex', justifyContent: direction === 'rtl' ? 'flex-end' : 'flex-start', alignItems: 'center' }}>
                <img src={logoHorizontalUrl} alt="Logo" style={{maxHeight: "57px", height: "100%"}} />
            </Box>
            <Box sx={{ position: "absolute", left: direction === 'rtl' ? 'auto' : '270px', right: direction === 'rtl' ? '270px' : 'auto', top: '10px', display: {xs: 'none', md: 'flex' }}}>
                {deliverContentsJobStatus && isPlatformAdmin && (
                    <Tooltip title={localeMessages["content_delivery_tooltip"]}>
                        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                            <Chip
                                size="small"
                                icon={statusConfig.icon}
                                label={localeMessages["content_delivery_job"]}
                                sx={(theme) => ({
                                    px: 0.75,
                                    borderRadius: 1.5,
                                    fontWeight: 500,
                                    color: theme.palette.status[statusConfig.paletteKey].text,
                                    backgroundColor: theme.palette.status[statusConfig.paletteKey].bg,
                                    border: `1px solid ${theme.palette.mode === 'dark' ? 'transparent' : theme.palette.status[statusConfig.paletteKey].border}`,
                                    '& .MuiChip-icon': {
                                        color: theme.palette.status[statusConfig.paletteKey].icon || theme.palette.status[statusConfig.paletteKey].text,
                                    },
                                })}
                            />
                            <Typography variant="caption" color="text.secondary">
                                {executionTime ? `${localeMessages["last_run"]} ${executionTime}` : localeMessages["never_run"]}
                            </Typography>
                        </Stack>
                    </Tooltip>
                )}
            </Box>
            <Box sx={{display: { xs: 'flex'}, right: direction === 'rtl' ? 'auto' : '0', left: direction === 'rtl' ? '0' : 'auto', position: "absolute", direction: direction, alignItems: 'center'}}>
                <ThemeSwitcher />
                <Box sx={{ m: 1, pt: '7px' }}>
                <IconButton
                    aria-controls="menu-appbar"
                    onClick={toggleMenuDrawer(true)}
                    disableRipple
                    disableFocusRipple
                    sx={(theme) => ({
                        display: { xs: 'inline-block', md: 'none' },
                        color: theme.palette.mode === 'light' ? theme.palette.grey[900] : 'inherit',
                        border: 'none',
                        outline: 'none',
                        boxShadow: 'none',
                        transition: 'ease 0.3s',
                        '&:hover': {
                            backgroundColor: 'transparent',
                            border: 'none',
                            color: theme.palette.primary.main,
                            outline: 'none',
                            boxShadow: 'none',
                        }
                    })}
                >
                    <MenuIcon />
                </IconButton>
                </Box>
            </Box>
        </AppBar>
        <Drawer anchor={direction === 'rtl' ? 'right' : 'left'} variant={drawerVariant} onClose={toggleMenuDrawer(false)} open={menuOpen} sx={{ '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth } }}
            slotProps={{ backdrop: { sx: { backgroundColor: 'rgba(251, 251, 255, 0.57)', backdropFilter: 'blur(5px)' }}, paper: { sx: { borderRadius: 0}}}}>
            <Box sx={{ my: 2, textAlign: 'center' }}>
                <img src={logoVerticalUrl} alt="Logo" style={{ width: "50%" }} />
            </Box>
            {
                showOrganizationSwitcher && <OrganizationsSelect organizations={organizations} activeOrganizationId={activeOrganizationId} changeOrganizationCallback={changeOrganizationCallback} sx={{ m: 2 }}  />
            }
            <MenuList>
                { pages.map((page) => {
                    const isActive = isActivePage(page.href);
                    return (
                    <MenuItem key={page.name} sx={(theme) => ({
                        backgroundColor: isActive ? (theme.palette.mode === 'dark' ? theme.palette.deepPurple[800] : theme.palette.deepPurple[50]) : 'transparent',
                        '& .MuiTouchRipple-root': {
                            color: theme.palette.secondary.main,
                        },
                        padding: 0,
                        '&:hover .MuiListItemIcon-root': { color: theme.palette.primary.dark }})}>
                        <Link
                            href={page.href}
                            underline="none"
                            color="inherit"
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                width: '100%',
                                py: '8px',
                                px: '16px',
                            }}
                        >
                        <ListItemIcon sx={(theme) => ({ minWidth: 35, color: theme.palette.mode === 'dark' ? theme.palette.deepPurple[300] : theme.palette.deepPurple[500] })}>
                            {page.icon}
                        </ListItemIcon>
                        <ListItemText
                            primary={page.name}
                            slotProps={{
                                primary: {
                                    fontSize: '0.95rem',
                                },
                            }}
                        />
                        </Link>
                    </MenuItem>
                )}) }
                {settingsPages.length > 0 && [
                    <MenuItem
                        key="settings-toggle"
                        onClick={() => setSettingsOpen(!settingsOpen)}
                        sx={(theme) => ({
                            backgroundColor: isSettingsSectionActive ? (theme.palette.mode === 'dark' ? theme.palette.deepPurple[800] : theme.palette.deepPurple[50]) : 'transparent',
                            '& .MuiTouchRipple-root': {
                                color: theme.palette.secondary.main,
                            },
                            '&:hover .MuiListItemIcon-root': { color: theme.palette.primary.dark },
                        })}
                    >
                        <ListItemIcon sx={(theme) => ({ minWidth: 35, color: theme.palette.mode === 'dark' ? theme.palette.deepPurple[300] : theme.palette.deepPurple[500] })}>
                            <SettingsOutlinedIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                            primary={localeMessages["settings"] || 'Settings'}
                            slotProps={{
                                primary: {
                                    fontSize: '0.95rem',
                                },
                            }}
                        />
                        {settingsOpen ? <ExpandLess /> : <ExpandMore />}
                    </MenuItem>,
                    <Collapse key="settings-collapse" in={settingsOpen} timeout="auto" unmountOnExit>
                        <MenuList disablePadding>
                            {settingsPages.map((page) => {
                                const isActive = isActivePage(page.href);
                                return (
                                    <MenuItem
                                        key={page.name}
                                        sx={(theme) => ({
                                            pl: 4,
                                            backgroundColor: isActive ? (theme.palette.mode === 'dark' ? theme.palette.deepPurple[800] : theme.palette.deepPurple[50]) : 'transparent',
                                            '& .MuiTouchRipple-root': {
                                                color: theme.palette.secondary.main,
                                            },
                                            '&:hover .MuiListItemIcon-root': { color: theme.palette.primary.dark },
                                        })}
                                    >
                                        <Link
                                            href={page.href}
                                            underline="none"
                                            color="inherit"
                                            sx={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                width: '100%',
                                                py: 0.1,
                                            }}
                                        >
                                            <ListItemIcon sx={(theme) => ({ minWidth: 35, color: theme.palette.mode === 'dark' ? theme.palette.deepPurple[300] : theme.palette.deepPurple[500] })}>
                                                {page.icon}
                                            </ListItemIcon>
                                            <ListItemText
                                                primary={page.name}
                                                slotProps={{
                                                    primary: {
                                                        fontSize: '0.95rem',
                                                    },
                                                }}
                                            />
                                        </Link>
                                    </MenuItem>
                                );
                            })}
                        </MenuList>
                    </Collapse>
                ]}
            </MenuList>
            {sidebarCustomComponent && <Box sx={{ height: "100px", width: "100%" }} dangerouslySetInnerHTML={{ __html: sidebarCustomComponent.componentTag }} />}
        </Drawer>
        </Box>)
}

export default MenuBar
