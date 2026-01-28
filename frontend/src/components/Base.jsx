import BottomDrawer from "./BottomDrawer";
import MenuBar from "./MenuBar";
import { useState, useEffect } from "react";
import { Box, GlobalStyles, Grid, Breadcrumbs, Typography, Link } from "@mui/material";
import { getCookie } from "../utils.js";


function Base({breadCrumbList, children, bottomDrawerParams, organizationIdRefreshCallback, showOrganizationSwitcher=true}) {
  const [activeOrganizationId, setActiveOrganizationId] = useState(null);
  const baseApiUrl = localStorage.getItem('apiBaseUrl');
  const drawerWidth = 250;

  useEffect(() => {
    const orgId = localStorage.getItem('activeOrganizationId');
    if (orgId) {
      console.log('Found saved organization ID:', orgId);
      setActiveOrganizationId(orgId);
    }
  }, []);

  useEffect(() => {
    if (organizationIdRefreshCallback) {
      organizationIdRefreshCallback(activeOrganizationId);
    }
    if (activeOrganizationId) {
      const localOrgId = localStorage.getItem('activeOrganizationId');
      if (localOrgId === activeOrganizationId) {
        return;
      }
      localStorage.setItem('activeOrganizationId', activeOrganizationId);
      fetch(baseApiUrl + '/session', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({
          active_organization_id: activeOrganizationId
        }),
      })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then((data) => {
        console.log('Session updated successfully:', data);
      })
      .catch((error) => {
        console.error('Error updating session:', error);
      });
    }
  }, [activeOrganizationId]);


  return (
   <>
    <GlobalStyles styles={(theme) => ({ body: { margin: 0, padding: 0, backgroundColor: theme.palette.background.dark, color: theme.palette.text.primary } })} />
    <MenuBar activeOrganizationId={activeOrganizationId} changeOrganizationCallback={setActiveOrganizationId} showOrganizationSwitcher={showOrganizationSwitcher} drawerWidth={drawerWidth} />
    <Box component="main"
        sx={{ flexGrow: 1, padding: {sm: 3, xs: 1, md: 5}, width: { md: `calc(100% - ${drawerWidth + 100}px)` }, float: { md: direction === 'rtl' ? 'left' : 'right' } }}>
    <Grid container spacing={0} mt={10} px={4}>
      <Grid size={{xs: 12}}>
      <Breadcrumbs aria-label="breadcrumb">
       { breadCrumbList.map(({label, href, index}) => (
         index < breadCrumbList.length - 1 ?
         <Link key={index} underline="hover" color="inherit" href={href}>
           {label}
         </Link> :
         <Typography key={index} sx={{ color: 'text.primary' }}>
           {label}
         </Typography>
       ))}
      </Breadcrumbs>
      </Grid>
    </Grid>
    <Grid container spacing={0}>
      {children}
      { bottomDrawerParams && <BottomDrawer icon={bottomDrawerParams.icon}>
        {bottomDrawerParams.children}
      </BottomDrawer>}
    </Grid>
    </Box>

    {/* Footer Credit */}
    <Box
      component="footer"
      sx={{
        position: 'fixed',
        bottom: 0,
        right: direction === 'rtl' ? 'auto' : 16,
        left: direction === 'rtl' ? 16 : 'auto',
        padding: 1,
        zIndex: 1000,
        backgroundColor: 'transparent'
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: 'text.secondary',
          fontSize: '0.7rem',
          opacity: 0.8
        }}
      >
        Powered by{' '}
        <Link
          href="https://www.avacodesolutions.com/"
          target="_blank"
          rel="noopener noreferrer"
          sx={{
            color: 'secondary.dark',
            textDecoration: 'none',
            '&:hover': {
              textDecoration: 'underline'
            }
          }}
        >
          AvaCode Solutions
        </Link>
        {' '}| BSD 3-Clause License
      </Typography>
    </Box>
    </>
  );
}

export default Base;
