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
import { useThemeContext } from '../theme/ThemeContext.jsx';
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
            { name: 'Organizations', icon: <Diversity3Icon fontSize="small" />, href:  platformBaseUrl + '/organizations/'},
        );
    }

    pages.push({ name: 'Course Management', icon: <SchoolIcon fontSize="small" />, href: platformBaseUrl + '/courses/' });
    pages.push({ name: 'Users', icon: <PeopleIcon fontSize="small" />, href: platformBaseUrl + '/users/' });
    pages.push({ name: 'Analytics', icon: <BarChartIcon fontSize="small" />, href: platformBaseUrl + '/analytics/' });


    const toggleMenuDrawer = (newOpen) => () => {
        setMenuOpen(newOpen);
    };

    return (

    // return (<AppBar sx={{boxShadow: 0, backgroundColor: 'white', borderBottom: '1px solid', borderColor: 'primary.main'}}>
    //     <Toolbar>
    //         <Box ml={2}>
    //         <img src={logoUrl} alt="Logo" style={{ height: 36 }} />
    //         </Box>
    //         <Typography variant="body1" component="span" sx={{ flexGrow: 1, ml: 2, color: 'primary.dark' }}>
    //         Email Learning
    //         {
    //             showOrganizationSwitcher &&  organizations.length > 0 && <OrganizationsSelect organizations={organizations} activeOrganizationId={activeOrganizationId} changeOrganizationCallback={changeOrganizationCallback} sx={{ display: { xs: 'none', md: 'inline-grid' } }} />
    //         }
    //         </Typography>
    //         <ThemeSwitcher />
    //         <Box sx={{display: { xs: 'flex', md: 'none'}, right: 0, position: "absolute" }}>
    //         <IconButton
    //             size="large"
    //             aria-label="account of current user"
    //             aria-controls="menu-appbar"
    //             aria-haspopup="true"
    //             onClick={toggleMenuDrawer(true)}
    //             color="primary"
    //             >
    //             <MenuIcon />
    //         </IconButton>
    //         </Box>

    //         <Box sx={{ float: "right", display: { xs: 'none', md: 'flex' } }}>
    //             {pages.map((page) => (
    //             <Button
    //                 key={page.name}
    //                 href={page.href}
    //                 sx={{ color: 'black', display: 'block', textTransform: 'none' }}
    //             >
    //                 {page.name}
    //             </Button>
    //             ))}
    //         </Box>
    //     </Toolbar>
        <Box component="nav"sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <AppBar sx={{boxShadow: 0, backgroundColor: 'background.nav', borderBottom: {xs: '1px solid', md: 'none'}, borderColor: {xs: 'primary.main', md: 'none'} }}>
            <Box my={1} ml={5}>
                <img src={logoHorizontalUrl} alt="Logo" style={{ height: 57 }} />
            </Box>
            <Box sx={{display: { xs: 'flex'}, right: 0, position: "absolute" }}>
                <ThemeSwitcher />
                <Box m={1} paddingTop="7px">
                <IconButton aria-controls="menu-appbar" onClick={toggleMenuDrawer(true)} sx={{ display: { xs: 'inline-block', md: 'none' }}}>
                    <MenuIcon />
                </IconButton>
                </Box>
            </Box>
        </AppBar>
        <Drawer variant={drawerVariant} onClose={toggleMenuDrawer(false)} display={{md: "none" }} open={menuOpen} sx={{ '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth } }}
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
