import { useState, useEffect } from 'react'
import { AppBar, Toolbar, Drawer, Box, Typography, MenuList, MenuItem, ListItemIcon, ListItemText, Button, Link, Select } from '@mui/material'
import IconButton from '@mui/material/IconButton';
import SchoolIcon from '@mui/icons-material/School';
import PeopleIcon from '@mui/icons-material/People';
import BarChartIcon from '@mui/icons-material/BarChart';
import Diversity3Icon from '@mui/icons-material/Diversity3';
import MenuIcon from '@mui/icons-material/Menu';
import logoUrl from '../assets/logo.png'
import { getCookie } from '../utils.js';

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

function MenuBar({activeOrganizationId, changeOrganizationCallback, showOrganizationSwitcher}) {
    const [menuOpen, setMenuOpen] = useState(false)
    const [organizations, setOrganizations] = useState([])

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

    return (<AppBar sx={{boxShadow: 0, backgroundColor: 'white', borderBottom: '1px solid', borderColor: 'primary.main'}}>
        <Toolbar>
            <Box ml={2}>
            <img src={logoUrl} alt="Logo" style={{ height: 36 }} />
            </Box>
            <Typography variant="body1" component="span" sx={{ flexGrow: 1, ml: 2, color: 'primary.dark' }}>
            Email Learning
            {
                showOrganizationSwitcher && <OrganizationsSelect organizations={organizations} activeOrganizationId={activeOrganizationId} changeOrganizationCallback={changeOrganizationCallback} sx={{ display: { xs: 'none', md: 'inline-grid' } }} />
            }
            </Typography>
            <Box sx={{display: { xs: 'flex', md: 'none'}, right: 0, position: "absolute" }}>
            <IconButton
                size="large"
                aria-label="account of current user"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                onClick={toggleMenuDrawer(true)}
                color="primary"
                >
                <MenuIcon />
            </IconButton>
            </Box>

            <Box sx={{ float: "right", display: { xs: 'none', md: 'flex' } }}>
                {pages.map((page) => (
                <Button
                    key={page.name}
                    href={page.href}
                    sx={{ color: 'black', display: 'block' }}
                >
                    {page.name}
                </Button>
                ))}
            </Box>
        </Toolbar>
        <Drawer open={menuOpen} onClose={toggleMenuDrawer(false)} display={{md: "none" }}
            slotProps={{ backdrop: { sx: { backgroundColor: 'rgba(251, 251, 255, 0.57)', backdropFilter: 'blur(5px)' }}, paper: { sx: { boxShadow: '2px 0px 8px rgba(0, 0, 0, 0.1)'}}}}>
            {
                showOrganizationSwitcher && <OrganizationsSelect organizations={organizations} activeOrganizationId={activeOrganizationId} changeOrganizationCallback={changeOrganizationCallback} sx={{ m: 2 }} />
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
        </AppBar>)
}

export default MenuBar
