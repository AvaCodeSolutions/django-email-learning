import { useState, useEffect, use } from 'react'
import { AppBar, Toolbar, Drawer, Box, Typography, MenuList, MenuItem, ListItemIcon, ListItemText, Button, Link, Select } from '@mui/material'
import IconButton from '@mui/material/IconButton';
import SchoolIcon from '@mui/icons-material/School';
import PeopleIcon from '@mui/icons-material/People';
import BarChartIcon from '@mui/icons-material/BarChart';
import Diversity3Icon from '@mui/icons-material/Diversity3';
import MenuIcon from '@mui/icons-material/Menu';
import logoHorizontalLightUrl from '../assets/logo-h-light.png'
import logoHorizontalDarkUrl from '../assets/logo-h-dark.png'
import logoVerticalLightUrl from '../assets/logo-v-light.png'
import logoVerticalDarkUrl from '../assets/logo-v-dark.png'
import { getCookie } from '../utils.js';
import { useTheme, useMediaQuery } from "@mui/material";
import ThemeSwitcher from './ThemeSwitcher.jsx';

const apiBaseUrl = localStorage.getItem('apiBaseUrl');
const platformBaseUrl = localStorage.getItem('platformBaseUrl');

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

    const theme = useTheme();
    const isMdUpScreen = useMediaQuery(theme.breakpoints.up('md'));

    const drawerVariant = isMdUpScreen ? "permanent" : "temporary";
    const logoHorizontalUrl = theme.palette.mode === 'light' ? logoHorizontalLightUrl : logoHorizontalDarkUrl;
    const logoVerticalUrl = theme.palette.mode === 'light' ? logoVerticalLightUrl : logoVerticalDarkUrl;

    useEffect(() => {
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

    if (localStorage.getItem('isPlatformAdmin') == 'true') {
        pages.push(
            { name: localeMessages["organizations"], icon: <Diversity3Icon fontSize="small" />, href:  platformBaseUrl + '/organizations/'},
        );
    }

    pages.push({ name: localeMessages["course_management"], icon: <SchoolIcon fontSize="small" />, href: platformBaseUrl + '/courses/' });
    pages.push({ name: localeMessages["learners"], icon: <PeopleIcon fontSize="small" />, href: platformBaseUrl + '/learners/' });
    // pages.push({ name: 'Analytics', icon: <BarChartIcon fontSize="small" />, href: platformBaseUrl + '/analytics/' });


    const toggleMenuDrawer = (newOpen) => () => {
        setMenuOpen(newOpen);
    };

    return (
        <Box component="nav"sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <AppBar sx={{boxShadow: 0, backgroundColor: 'background.nav', borderBottom: {xs: '1px solid', md: 'none'}, borderColor: {xs: 'primary.main', md: 'none'} }}>
            <Box my={1} ml={5} sx={{ height: {xs: "57px", md: "30px"}}}>
                <img src={logoHorizontalUrl} alt="Logo" style={{maxHeight: "57px", height: "100%"}} />
            </Box>
            <Box sx={{display: { xs: 'flex'}, right: direction === 'rtl' ? 'auto' : '0', left: direction === 'rtl' ? '0' : 'auto', position: "absolute" }}>
                <ThemeSwitcher />
                <Box m={1} paddingTop="7px">
                <IconButton aria-controls="menu-appbar" onClick={toggleMenuDrawer(true)} sx={{ display: { xs: 'inline-block', md: 'none' }}}>
                    <MenuIcon />
                </IconButton>
                </Box>
            </Box>
        </AppBar>
        <Drawer anchor={direction === 'rtl' ? 'right' : 'left'} variant={drawerVariant} onClose={toggleMenuDrawer(false)} display={{md: "none" }} open={menuOpen} sx={{ '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth } }}
            slotProps={{ backdrop: { sx: { backgroundColor: 'rgba(251, 251, 255, 0.57)', backdropFilter: 'blur(5px)' }}, paper: { sx: { boxShadow: '2px 0px 8px rgba(0, 0, 0, 0.1)'}}}}>
            <Box my={2} textAlign="center">
                <img src={logoVerticalUrl} alt="Logo" style={{ width: "50%" }} />
            </Box>
            {
                showOrganizationSwitcher && <OrganizationsSelect organizations={organizations} activeOrganizationId={activeOrganizationId} changeOrganizationCallback={changeOrganizationCallback} sx={{ m: 2 }}  />
            }
            <MenuList>
                { pages.map((page) => (
                    <MenuItem key={page.name}>
                        <Link href={page.href} underline="none" color="inherit" sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        <ListItemIcon>
                            {page.icon}
                        </ListItemIcon>
                        <ListItemText>{page.name}</ListItemText>
                        </Link>
                    </MenuItem>
                )) }
            </MenuList>
        </Drawer>
        </Box>)
}

export default MenuBar
