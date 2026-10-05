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
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import logoHorizontalLightUrl from '../assets/logo-h-light.png'
import logoHorizontalDarkUrl from '../assets/logo-h-dark.png'
import logoVerticalLightUrl from '../assets/logo-v-light.png'
import logoVerticalDarkUrl from '../assets/logo-v-dark.png'
import logoMarkUrl from '../assets/logo.png'
import { sanitizeComponentHtml } from '../sanitizeHtml.js';
import { sanitizeEndpointUrl, sanitizeImageUrl, sanitizeUrl } from '../sanitizeUrl.js';
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

function NavItem({ page, isActive, isExactMatch, mini, tooltipPlacement }) {
    const icon = (
        <ListItemIcon sx={(theme) => ({ minWidth: mini ? 0 : 30, color: alpha(theme.palette.text.primary, 0.6), '& .MuiSvgIcon-root': { fontSize: '1.1rem' } })}>
            {page.icon}
        </ListItemIcon>
    );
    const text = mini ? null : (
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

    // In the mini drawer the label is hidden, so it moves to a tooltip and an
    // aria-label to stay discoverable and accessible.
    const withTooltip = (element) => mini ? (
        // describeChild stops Tooltip from also putting the label on the <li>;
        // the aria-label below sits on the focusable link instead.
        <Tooltip title={page.name} placement={tooltipPlacement} describeChild>{element}</Tooltip>
    ) : element;
    const itemPadding = mini ? { py: '10px', px: 0, justifyContent: 'center' } : { py: '8px', px: '16px' };

    if (isExactMatch) {
        return withTooltip(
            <Box
                component="li"
                aria-current="page"
                aria-label={mini ? page.name : undefined}
                sx={(theme) => ({
                    display: 'flex',
                    alignItems: 'center',
                    ...itemPadding,
                    ...activeStyles(theme),
                })}
            >
                {icon}
                {text}
            </Box>
        );
    }

    return withTooltip(
        <MenuItem sx={(theme) => ({
            ...(isActive ? activeStyles(theme) : { backgroundColor: 'transparent', borderInlineStart: '3px solid transparent' }),
            '& .MuiTouchRipple-root': { color: theme.palette.primary.main },
            // MUI's MenuItem ships its own `.MuiMenuItem-root .MuiListItemIcon-root { minWidth: 36px }`
            // rule with higher specificity than a plain sx on ListItemIcon, so it silently wins over
            // the 30px set in NavItem's `icon` unless forced here.
            '& .MuiListItemIcon-root': { minWidth: mini ? '0 !important' : '30px !important' },
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
                aria-label={mini ? page.name : undefined}
                sx={{ display: 'flex', alignItems: 'center', width: '100%', ...itemPadding }}
            >
                {icon}
                {text}
            </Link>
        </MenuItem>
    );
}

function MenuBar({activeOrganizationId, changeOrganizationCallback, showOrganizationSwitcher, drawerWidth, miniDrawerWidth}) {
    const [menuOpen, setMenuOpen] = useState(false)
    const [organizations, setOrganizations] = useState([])
    const [deliverContentsJobStatus, setDeliverContentsJobStatus] = useState(null)
    const { localeMessages, isPlatformAdmin, isOrganizationAdmin, isInstructor, direction, apiBaseUrl: rawApiBaseUrl, platformBaseUrl: rawPlatformBaseUrl, sidebarCustomComponent, navbarCustomComponents, customLogo } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const platformBaseUrl = sanitizeUrl(rawPlatformBaseUrl);

    const theme = useTheme();
    const isMdUpScreen = useMediaQuery(theme.breakpoints.up('md'));
    const isXlUpScreen = useMediaQuery(theme.breakpoints.up('xl'));
    // md–xl gets a permanent icon-only drawer; the full drawer is permanent
    // only from xl up. Below xl the full drawer is still reachable as a
    // temporary overlay through the app bar's menu button.
    const showPermanentFullDrawer = isXlUpScreen;
    const showPermanentMiniDrawer = isMdUpScreen && !isXlUpScreen;
    const drawerAnchor = direction === 'rtl' ? 'right' : 'left';
    const tooltipPlacement = direction === 'rtl' ? 'left' : 'right';
    const currentPath = typeof window !== 'undefined' ? window.location.pathname.replace(/\/+$/, '') || '/' : '/';
    let logoHorizontalUrl, logoVerticalUrl, logoMarkCustomUrl;
    if (customLogo) {
        // Sanitized here rather than at the <img> below so that an unusable
        // custom logo falls through to the bundled default instead of
        // rendering a broken image.
        const horizontalLight = sanitizeImageUrl(customLogo.horizontalLight);
        const horizontalDark = sanitizeImageUrl(customLogo.horizontalDark);
        const verticalLight = sanitizeImageUrl(customLogo.verticalLight);
        const verticalDark = sanitizeImageUrl(customLogo.verticalDark);
        const markLight = sanitizeImageUrl(customLogo.markLight);
        const markDark = sanitizeImageUrl(customLogo.markDark);
        logoHorizontalUrl = theme.palette.mode === 'light' ? (horizontalLight ? horizontalLight : horizontalDark) : (horizontalDark ? horizontalDark : horizontalLight);
        logoVerticalUrl = theme.palette.mode === 'light' ? (verticalLight ? verticalLight : verticalDark) : (verticalDark ? verticalDark : verticalLight);
        logoMarkCustomUrl = theme.palette.mode === 'light' ? (markLight ? markLight : markDark) : (markDark ? markDark : markLight);
    }
    if (!logoHorizontalUrl) {
        logoHorizontalUrl = theme.palette.mode === 'light' ? logoHorizontalLightUrl : logoHorizontalDarkUrl;
    }
    // The mini drawer drops the logo text and shows only the mark. Without a
    // custom mark, a custom vertical lockup is used as-is there, so a site
    // that brands the sidebar never falls back to the bundled mark.
    const logoMiniUrl = logoMarkCustomUrl || logoVerticalUrl || logoMarkUrl;
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

    const sectionDivider = (label, mini) => mini ? (
        <Divider sx={{ my: 1 }} />
    ) : (
        <Divider textAlign="left" sx={{ mt: 1, mb: 0.5 }}>
            <Typography variant="caption" sx={(theme) => ({ color: theme.palette.mode === 'dark' ? theme.palette.text.secondary : theme.palette.text.disabled, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.7rem' })}>
                {label}
            </Typography>
        </Divider>
    );

        const healthStatus = deliverContentsJobStatus?.job_health_status || 'healthy';
        const statusConfig = jobsStatusMap[healthStatus] || jobsStatusMap.healthy;
        const executionTime = deliverContentsJobStatus?.last_execution_started_at
            ? new Date(deliverContentsJobStatus.last_execution_started_at).toLocaleString()
            : null;


    // Arrows point away from the drawer's anchor to expand and back toward it
    // to collapse, so they flip with the text direction.
    const ExpandIcon = direction === 'rtl' ? ChevronLeftIcon : ChevronRightIcon;
    const CollapseIcon = direction === 'rtl' ? ChevronRightIcon : ChevronLeftIcon;
    const drawerToggleButtonSx = (theme) => ({
        p: 0.25,
        color: alpha(theme.palette.text.primary, 0.6),
        border: `1px solid ${alpha(theme.palette.border.main, 0.4)}`,
        '&:hover': { backgroundColor: theme.palette.primary.main, borderColor: theme.palette.primary.main, color: '#ffffff' },
    });

    // `expandedFromMini` is the full drawer opened over the content from the
    // mini drawer (md–xl); it gets an arrow to collapse back.
    const renderDrawerContent = (mini, expandedFromMini = false) => (
        <>
            <Box sx={{ my: 2, textAlign: 'center', position: 'relative' }}>
                <img src={mini ? logoMiniUrl : logoVerticalUrl} alt="Logo" style={{ width: mini ? "60%" : "50%" }} />
                {expandedFromMini && (
                    <IconButton
                        size="small"
                        aria-label="Collapse menu"
                        onClick={toggleMenuDrawer(false)}
                        sx={(theme) => ({ ...drawerToggleButtonSx(theme), position: 'absolute', top: 0, insetInlineEnd: 8 })}
                    >
                        <CollapseIcon fontSize="small" />
                    </IconButton>
                )}
            </Box>
            {mini && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
                    <Tooltip title="Expand menu" placement={tooltipPlacement}>
                        <IconButton
                            size="small"
                            aria-label="Expand menu"
                            onClick={toggleMenuDrawer(true)}
                            sx={drawerToggleButtonSx}
                        >
                            <ExpandIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                </Box>
            )}
            {
                !mini && showOrganizationSwitcher && <OrganizationsSelect organizations={organizations} activeOrganizationId={activeOrganizationId} changeOrganizationCallback={changeOrganizationCallback} />
            }
            <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden' }}>
            <MenuList>
                {/* ── Administration ── (org admin only) */}
                {adminPages.length > 0 && <>
                    {sectionDivider(localeMessages['administration'] || 'Administration', mini)}
                    {adminPages.map((page) => <NavItem key={page.name} page={page} isActive={isActivePage(page.href)} isExactMatch={isCurrentPage(page.href)} mini={mini} tooltipPlacement={tooltipPlacement} />)}
                </>}

                {/* ── Platform ── */}
                {sectionDivider(localeMessages['platform_section'] || 'Platform', mini)}
                {platformPages.map((page) => <NavItem key={page.name} page={page} isActive={page.exactOnly ? isCurrentPage(page.href) : isActivePage(page.href)} isExactMatch={isCurrentPage(page.href)} mini={mini} tooltipPlacement={tooltipPlacement} />)}

                {/* ── Settings ── (platform admin only, always expanded) */}
                {settingsPages.length > 0 && <>
                    {sectionDivider(localeMessages['settings'] || 'Settings', mini)}
                    {settingsPages.map((page) => <NavItem key={page.name} page={page} isActive={isActivePage(page.href)} isExactMatch={isCurrentPage(page.href)} mini={mini} tooltipPlacement={tooltipPlacement} />)}
                </>}

                {/* ── Appearance ── */}
                {sectionDivider(localeMessages['appearance'] || 'Appearance', mini)}
                <ThemeSwitcher mini={mini} tooltipPlacement={tooltipPlacement} />

                {/* ── System ── (platform admin only) */}
                {deliverContentsJobStatus && isPlatformAdmin && <>
                    {sectionDivider(localeMessages['system'] || 'System', mini)}
                    {mini ? (
                        <Tooltip
                            title={`${localeMessages["content_delivery_job"]}: ${executionTime ? `${localeMessages["last_run"]} ${executionTime}` : localeMessages["never_run"]}`}
                            placement={tooltipPlacement}
                        >
                            <Box
                                aria-label={localeMessages["content_delivery_job"]}
                                sx={{ display: 'flex', justifyContent: 'center', py: 1.25, cursor: 'default' }}
                            >
                                <Box sx={(theme) => ({
                                    width: 10, height: 10, borderRadius: '50%',
                                    backgroundColor: theme.palette.status[statusConfig.paletteKey].icon || theme.palette.status[statusConfig.paletteKey].text,
                                })} />
                            </Box>
                        </Tooltip>
                    ) : (
                    <Tooltip title={localeMessages["content_delivery_tooltip"]} placement={tooltipPlacement}>
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
                    )}
                </>}
            </MenuList>
            </Box>
            {!mini && (navbarCustomComponents?.length > 0 || sidebarCustomComponent) && (
                <Box sx={{ mt: 'auto' }}>
                    {navbarCustomComponents?.map((component) => (
                        <Box
                            key={component.slot}
                            sx={{ display: { xs: 'block', md: 'none' }, py: '8px' }}
                            dangerouslySetInnerHTML={{ __html: sanitizeComponentHtml(component.html) }}
                        />
                    ))}
                    {sidebarCustomComponent && <Box dangerouslySetInnerHTML={{ __html: sanitizeComponentHtml(sidebarCustomComponent.componentTag) }} />}
                </Box>
            )}
        </>
    );

    return (
        <Box component="nav" sx={{ width: { md: miniDrawerWidth, xl: drawerWidth }, flexShrink: { md: 0 } }}>
        <AppBar sx={(theme) => ({boxShadow: 0, borderRadius: 0, backgroundColor: 'background.nav', borderBottom: `1px solid ${alpha(theme.palette.border.main, 0.4)}` })}>
            <Box sx={{ my: 1, ml: { xs: 1, sm: 5 }, height: { xs: "57px", md: "30px" }, display: 'flex', justifyContent: direction === 'rtl' ? 'flex-end' : 'flex-start', alignItems: 'center' }}>
                {/* From md up the permanent drawer carries the logo, so the app bar's copy is hidden. */}
                <Box component="img" src={logoHorizontalUrl} alt="Logo" sx={{ maxHeight: "57px", height: "100%", display: { xs: 'block', md: 'none' } }} />
            </Box>
            <Box sx={{display: { xs: 'flex'}, right: direction === 'rtl' ? 'auto' : 5, left: direction === 'rtl' ? 5 : 'auto', position: "absolute", top: '50%', transform: 'translateY(-50%)', direction: direction, alignItems: 'center'}}>
                {navbarCustomComponents?.map((component) => (
                    <Box key={component.slot} sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }} dangerouslySetInnerHTML={{ __html: sanitizeComponentHtml(component.html) }} />
                ))}
                <Box sx={{ m: 1 }}>
                <IconButton
                    aria-controls="menu-appbar"
                    aria-label="Open menu"
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
        {(showPermanentFullDrawer || showPermanentMiniDrawer) && (
            <Drawer anchor={drawerAnchor} variant="permanent" open
                sx={{ '& .MuiDrawer-paper': { boxSizing: 'border-box', width: showPermanentFullDrawer ? drawerWidth : miniDrawerWidth, display: 'flex', flexDirection: 'column', backgroundColor: 'background.nav', overflowX: 'hidden' } }}
                slotProps={{ paper: { sx: { borderRadius: 0, boxShadow: 'none'}}}}>
                {renderDrawerContent(showPermanentMiniDrawer)}
            </Drawer>
        )}
        {!showPermanentFullDrawer && (
            <Drawer anchor={drawerAnchor} variant="temporary" onClose={toggleMenuDrawer(false)} open={menuOpen} sx={{ '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth, display: 'flex', flexDirection: 'column', backgroundColor: 'background.nav' } }}
                slotProps={{ backdrop: { sx: { backgroundColor: 'rgba(0, 0, 0, 0.15)', backdropFilter: 'blur(5px)' }}, paper: { sx: { borderRadius: 0, boxShadow: 'none'}}}}>
                {renderDrawerContent(false, isMdUpScreen)}
            </Drawer>
        )}
        </Box>)
}

export default MenuBar
