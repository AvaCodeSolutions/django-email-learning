import BottomDrawer from "./BottomDrawer";
import MenuBar from "./MenuBar";
import { useState, useEffect } from "react";
import { Box, GlobalStyles, Grid, Breadcrumbs, Typography, Link } from "@mui/material";
import { getCookie } from "../utils.js";
import { useAppContext } from "../render.jsx";


function Base({breadCrumbList, children, bottomDrawerParams, organizationIdRefreshCallback, showOrganizationSwitcher=true}) {
  const { direction, apiBaseUrl } = useAppContext();
  const [activeOrganizationId, setActiveOrganizationId] = useState(null);
  const drawerWidth = 250;
  const activeCrumbIndex = breadCrumbList.length - 1;

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
      fetch(apiBaseUrl + '/session', {
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
    <GlobalStyles styles={(theme) => ({ body: { margin: 0, padding: 0, backgroundColor: theme.palette.background.main, color: theme.palette.text.primary } })} />
    <MenuBar activeOrganizationId={activeOrganizationId} changeOrganizationCallback={setActiveOrganizationId} showOrganizationSwitcher={showOrganizationSwitcher} drawerWidth={drawerWidth} />
    <Box sx={{ width: { md: `calc(100% - ${drawerWidth}px)` }, float: { md: direction === 'rtl' ? 'left' : 'right' }, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
    <Box component="main"
      sx={{ flexGrow: 1, padding: {xs: 0, sm: 3, md: 3}, maxWidth: '1400px', width: '100%' }}>
    <Grid container spacing={0} sx={{ mt: { xs: 12, md: 6 }, px: { xs: 1, sm: 4 } }}>
      <Grid size={{xs: 12}}>
      <Breadcrumbs
        aria-label="breadcrumb"
        maxItems={3}
        separator="›"
        dir={direction}
        sx={{
          direction: direction,
          '& .MuiBreadcrumbs-ol': {
            justifyContent: 'flex-start',
          },
          '& .MuiBreadcrumbs-separator': {
            color: 'text.disabled',
            opacity: 0.55,
            fontSize: { xs: '0.85rem', sm: '0.92rem', md: '1.2rem' },
            mx: 0.75,
          },
        }}
      >
       { breadCrumbList.map(({label, href}, index) => (
         index !== activeCrumbIndex ?
         <Link
           key={index}
           underline="hover"
           href={href}
           sx={(theme) => ({
             fontSize: { xs: '0.85rem', sm: '0.92rem', md: '1.15rem' },
             lineHeight: 1.3,
             color: theme.palette.mode === 'dark' ? theme.palette.link?.main ?? theme.palette.primary.light : theme.palette.primary.dark,
             transition: 'opacity 0.2s ease',
             '&:hover': {
               opacity: 0.8,
             },
           })}
         >
           {label}
         </Link> :
         <Typography
           key={index}
           variant="body1"
           sx={{
             color: 'text.primary',
             fontWeight: 400,
             fontSize: { xs: '0.85rem', sm: '0.92rem', md: '1.2rem' },
             lineHeight: 1.3,
           }}
         >
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
        textAlign: direction === 'rtl' ? 'left' : 'right',
        py: 1,
        paddingInlineEnd: 1,
        mt: 'auto',
      }}
    >
      <Typography
        variant="caption"
        sx={(theme) => ({
          color: theme.palette.mode === 'dark' ? theme.palette.text.primary : theme.palette.text.secondary,
        })}
      >
        Powered by{' '}
        <Link
          href="https://www.avacodesolutions.com/"
          target="_blank"
          rel="noopener noreferrer"
          sx={(theme) => ({
            color: theme.palette.mode === 'dark' ? theme.palette.link?.main : 'primary.dark',
            textDecoration: 'none',
            '&:hover': {
              textDecoration: 'underline'
            }
          })}
        >
          AvaCode Solutions
        </Link>
        {' '}| BSD 3-Clause License
      </Typography>
    </Box>
    </Box>
    </>
  );
}

export default Base;
