import { useState, useEffect } from 'react'
import { alpha } from '@mui/material/styles'
import { AppBar, Divider, Drawer, Box, Typography, MenuList, MenuItem, ListItemIcon, ListItemText, Tooltip, Link, Select } from '@mui/material'
import IconButton from '@mui/material/IconButton';
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import SchoolOutlinedIcon from '@mui/icons-material/SchoolOutlined';
import PeopleOutlinedIcon from '@mui/icons-material/PeopleOutlined';
import BarChartOutlinedIcon from '@mui/icons-material/BarChartOutlined';
import DoneIcon from '@mui/icons-material/Done';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import VpnKeyOutlinedIcon from '@mui/icons-material/VpnKeyOutlined';
import CorporateFareOutlinedIcon from '@mui/icons-material/CorporateFareOutlined';
import MenuIcon from '@mui/icons-material/Menu';
import logoHorizontalLightUrl from '../assets/logo-h-light.png'
import logoHorizontalDarkUrl from '../assets/logo-h-dark.png'
import logoVerticalLightUrl from '../assets/logo-v-light.png'
import logoVerticalDarkUrl from '../assets/logo-v-dark.png'
import { getCookie } from '../utils.js';
import { useTheme, useMediaQuery } from "@mui/material";
import ThemeSwitcher from './ThemeSwitcher.jsx';
import { useAppContext } from '../render.jsx';


function OrganizationsSelect({organizations, activeOrganizationId, changeOrganizationCallback}) {
    return (
        <Box sx={{ px: 2, pb: 1 }}>
            <Typography variant="caption" sx={(theme) => ({ color: theme.palette.mode === 'dark' ? theme.palette.text.secondary : theme.palette.text.disabled, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.65rem', display: 'block', mb: 0.75 })}>
                Organization
            </Typography>
            <Select
                value={activeOrganizationId ? String(activeOrganizationId) : ""}
                onChange={(e) => changeOrganizationCallback(e.target.value)}
                displayEmpty
                inputProps={{ 'aria-label': 'Select organization' }}
                sx={{
                    width: '100%',
                    fontSize: 16,
                    '& .MuiSelect-select': { paddingTop: '8px', paddingBottom: '8px' },
                    '& .MuiSvgIcon-root': { top: 'calc(50% - 12px)' },
                }}
            >
                {organizations.map((org) => (
                    <MenuItem key={org.id} value={String(org.id)}>
                        {org.name}
                    </MenuItem>
                ))}
            </Select>
        </Box>
    )
}

function NavItem({ page, isActive, isExactMatch }) {
    const icon = (
        <ListItemIcon sx={(theme) => ({ minWidth: 30, color: alpha(theme.palette.text.primary, 0.6), '& .MuiSvgIcon-root': { fontSize: '1.1rem' } })}>
            {page.icon}
        </ListItemIcon>
    );
    const text = (
        <ListItemText
            primary={page.name}
            slotProps={{ primary: { fontSize: '0.9rem', fontWeight: isActive ? 600 : 400, color: 'inherit' } }}
        />
    );
    const activeStyles = (theme) => ({
        backgroundColor: theme.palette.mode === 'dark'
            ? alpha(theme.palette.primary.main, 0.18)
            : alpha(theme.palette.background.dark, 0.5),
        borderInlineStart: `3px solid ${theme.palette.primary.main}`,
    });

    if (isExactMatch) {
        return (
            <Box
                component="li"
                aria-current="page"
                sx={(theme) => ({
                    display: 'flex',
                    alignItems: 'center',
                    py: '8px',
                    px: '16px',
                    ...activeStyles(theme),
                })}
            >
                {icon}
                {text}
            </Box>
        );
    }

    return (
        <MenuItem sx={(theme) => ({
            ...(isActive ? activeStyles(theme) : { backgroundColor: 'transparent', borderInlineStart: '3px solid transparent' }),
            '& .MuiTouchRipple-root': { color: theme.palette.primary.main },
            // MUI's MenuItem ships its own `.MuiMenuItem-root .MuiListItemIcon-root { minWidth: 36px }`
            // rule with higher specificity than a plain sx on ListItemIcon, so it silently wins over
            // the 30px set in NavItem's `icon` unless forced here.
            '& .MuiListItemIcon-root': { minWidth: '30px !important' },
            padding: 0,
            '&:hover': {
                backgroundColor: theme.palette.primary.main,
            },
            '&:hover .MuiListItemIcon-root': { color: '#ffffff' },
            '&:hover .MuiListItemText-primary': { color: '#ffffff' },
        })}>
            <Link
                href={page.href}
                underline="none"
                color="inherit"
                sx={{ display: 'flex', alignItems: 'center', width: '100%', py: '8px', px: '16px' }}
            >
                {icon}
                {text}
            </Link>
        </MenuItem>
    );
}

function MenuBar({activeOrganizationId, changeOrganizationCallback, showOrganizationSwitcher, drawerWidth}) {
    const [menuOpen, setMenuOpen] = useState(false)
    const [organizations, setOrganizations] = useState([])
    const [deliverContentsJobStatus, setDeliverContentsJobStatus] = useState(null)
    const { localeMessages, isPlatformAdmin, isOrganizationAdmin, isInstructor, direction, apiBaseUrl, platformBaseUrl, sidebarCustomComponent, navbarCustomComponents, customLogo } = useAppContext();

    const theme = useTheme();
    const isMdUpScreen = useMediaQuery(theme.breakpoints.up('md'));

    const drawerVariant = isMdUpScreen ? "permanent" : "temporary";
    const currentPath = typeof window !== 'undefined' ? window.location.pathname.replace(/\/+$/, '') || '/' : '/';
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
        // Only platform admins can read job status (and only they see the
        // indicator below), so don't spend a request that would 403 for anyone else.
        if (isPlatformAdmin) {
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
        }

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

    const adminPages = []
    if (isOrganizationAdmin) {
        adminPages.push(
            { name: localeMessages["organizations"], icon: <CorporateFareOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/organizations/' },
        );
    }

    const platformPages = []
    // Dashboard's href is the platform section's root, so it's a path-prefix
    // of every other page here — exactOnly keeps it from matching (and
    // highlighting) on all of them.
    platformPages.push({ name: localeMessages["dashboard"], icon: <DashboardOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/', exactOnly: true });
    platformPages.push({ name: localeMessages["course_management"], icon: <SchoolOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/courses/' });
    if (isOrganizationAdmin || isPlatformAdmin || isInstructor) {
        platformPages.push({ name: localeMessages["learners"], icon: <PeopleOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/learners/' });
    }
    platformPages.push({ name: localeMessages["analytics"], icon: <BarChartOutlinedIcon fontSize="small" />, href: platformBaseUrl + '/analytics/' });

    const settingsPages = []
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

    const isCurrentPage = (href) => {
        if (typeof window === 'undefined') {
            return false;
        }
        const pagePath = new URL(href, window.location.origin).pathname.replace(/\/+$/, '') || '/';
        return currentPath === pagePath;
    };

        const healthStatus = deliverContentsJobStatus?.job_health_status || 'healthy';
        const statusConfig = jobsStatusMap[healthStatus] || jobsStatusMap.healthy;
        const executionTime = deliverContentsJobStatus?.last_execution_started_at
            ? new Date(deliverContentsJobStatus.last_execution_started_at).toLocaleString()
            : null;


    return (
        <Box component="nav"sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <AppBar sx={(theme) => ({boxShadow: 0, borderRadius: 0, backgroundColor: 'background.nav', borderBottom: `1px solid ${alpha(theme.palette.border.main, 0.4)}` })}>
            <Box sx={{ my: 1, ml: { xs: 1, sm: 5 }, height: { xs: "57px", md: "30px" }, display: 'flex', justifyContent: direction === 'rtl' ? 'flex-end' : 'flex-start', alignItems: 'center' }}>
                <img src={logoHorizontalUrl} alt="Logo" style={{maxHeight: "57px", height: "100%"}} />
            </Box>
            <Box sx={{display: { xs: 'flex'}, right: direction === 'rtl' ? 'auto' : 5, left: direction === 'rtl' ? 5 : 'auto', position: "absolute", top: '50%', transform: 'translateY(-50%)', direction: direction, alignItems: 'center'}}>
                {navbarCustomComponents?.map((component) => (
                    <Box key={component.slot} sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }} dangerouslySetInnerHTML={{ __html: component.html }} />
                ))}
                <Box sx={{ m: 1 }}>
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
        <Drawer anchor={direction === 'rtl' ? 'right' : 'left'} variant={drawerVariant} onClose={toggleMenuDrawer(false)} open={menuOpen} sx={{ '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth, display: 'flex', flexDirection: 'column', backgroundColor: 'background.nav' } }}
            slotProps={{ backdrop: { sx: { backgroundColor: 'rgba(0, 0, 0, 0.15)', backdropFilter: 'blur(5px)' }}, paper: { sx: { borderRadius: 0, boxShadow: 'none'}}}}>
            <Box sx={{ my: 2, textAlign: 'center' }}>
                <img src={logoVerticalUrl} alt="Logo" style={{ width: "50%" }} />
            </Box>
            {
                showOrganizationSwitcher && <OrganizationsSelect organizations={organizations} activeOrganizationId={activeOrganizationId} changeOrganizationCallback={changeOrganizationCallback} />
            }
            <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
            <MenuList>
                {/* ── Administration ── (org admin only) */}
                {adminPages.length > 0 && <>
                    <Divider textAlign="left" sx={{ mt: 1, mb: 0.5 }}>
                        <Typography variant="caption" sx={(theme) => ({ color: theme.palette.mode === 'dark' ? theme.palette.text.secondary : theme.palette.text.disabled, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.7rem' })}>
                            {localeMessages['administration'] || 'Administration'}
                        </Typography>
                    </Divider>
                    {adminPages.map((page) => <NavItem key={page.name} page={page} isActive={isActivePage(page.href)} isExactMatch={isCurrentPage(page.href)} />)}
                </>}

                {/* ── Platform ── */}
                <Divider textAlign="left" sx={{ mt: 1, mb: 0.5 }}>
                    <Typography variant="caption" sx={(theme) => ({ color: theme.palette.mode === 'dark' ? theme.palette.text.secondary : theme.palette.text.disabled, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.7rem' })}>
                        {localeMessages['platform_section'] || 'Platform'}
                    </Typography>
                </Divider>
                {platformPages.map((page) => <NavItem key={page.name} page={page} isActive={page.exactOnly ? isCurrentPage(page.href) : isActivePage(page.href)} isExactMatch={isCurrentPage(page.href)} />)}

                {/* ── Settings ── (platform admin only, always expanded) */}
                {settingsPages.length > 0 && <>
                    <Divider textAlign="left" sx={{ mt: 1, mb: 0.5 }}>
                        <Typography variant="caption" sx={(theme) => ({ color: theme.palette.mode === 'dark' ? theme.palette.text.secondary : theme.palette.text.disabled, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.7rem' })}>
                            {localeMessages['settings'] || 'Settings'}
                        </Typography>
                    </Divider>
                    {settingsPages.map((page) => <NavItem key={page.name} page={page} isActive={isActivePage(page.href)} isExactMatch={isCurrentPage(page.href)} />)}
                </>}

                {/* ── Appearance ── */}
                <Divider textAlign="left" sx={{ mt: 1, mb: 0.5 }}>
                    <Typography variant="caption" sx={(theme) => ({ color: theme.palette.mode === 'dark' ? theme.palette.text.secondary : theme.palette.text.disabled, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.7rem' })}>
                        {localeMessages['appearance'] || 'Appearance'}
                    </Typography>
                </Divider>
                <ThemeSwitcher />

                {/* ── System ── (platform admin only) */}
                {deliverContentsJobStatus && isPlatformAdmin && <>
                    <Divider textAlign="left" sx={{ mt: 1, mb: 0.5 }}>
                        <Typography variant="caption" sx={(theme) => ({ color: theme.palette.mode === 'dark' ? theme.palette.text.secondary : theme.palette.text.disabled, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.7rem' })}>
                            {localeMessages['system'] || 'System'}
                        </Typography>
                    </Divider>
                    <Tooltip title={localeMessages["content_delivery_tooltip"]} placement="right">
                        <Box sx={(theme) => ({
                            mx: 2, my: 1, px: 1.5, py: 1.25,
                            borderRadius: 2,
                            backgroundColor: theme.palette.status[statusConfig.paletteKey].bg,
                            border: `1px solid ${theme.palette.mode === 'dark' ? 'transparent' : theme.palette.status[statusConfig.paletteKey].border}`,
                            cursor: 'default',
                        })}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
                                <Box sx={(theme) => ({
                                    width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                                    backgroundColor: theme.palette.status[statusConfig.paletteKey].icon || theme.palette.status[statusConfig.paletteKey].text,
                                })} />
                                <Typography sx={(theme) => ({ fontSize: '0.78rem', fontWeight: 600, color: theme.palette.status[statusConfig.paletteKey].text, lineHeight: 1 })}>
                                    {localeMessages["content_delivery_job"]}
                                </Typography>
                            </Box>
                            <Typography variant="caption" sx={(theme) => ({ color: theme.palette.status[statusConfig.paletteKey].text, opacity: 0.75 })}>
                                {executionTime ? `${localeMessages["last_run"]} ${executionTime}` : localeMessages["never_run"]}
                            </Typography>
                        </Box>
                    </Tooltip>
                </>}
            </MenuList>
            </Box>
            {(navbarCustomComponents?.length > 0 || sidebarCustomComponent) && (
                <Box sx={{ mt: 'auto' }}>
                    {navbarCustomComponents?.map((component) => (
                        <Box
                            key={component.slot}
                            sx={{ display: { xs: 'block', md: 'none' }, py: '8px' }}
                            dangerouslySetInnerHTML={{ __html: component.html }}
                        />
                    ))}
                    {sidebarCustomComponent && <Box dangerouslySetInnerHTML={{ __html: sidebarCustomComponent.componentTag }} />}
                </Box>
            )}
        </Drawer>
        </Box>)
}

export default MenuBar
