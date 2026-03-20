import BottomDrawer from "./BottomDrawer";
import MenuBar from "./MenuBar";
import * as React from "react";
import * as ReactDom from "react-dom";
import * as MaterialUI from "@mui/material";
import { useState, useEffect } from "react";
import { Box, Button, Select, GlobalStyles, Grid, Breadcrumbs, Typography, Link } from "@mui/material";
import { getCookie } from "../utils.js";
import { useAppContext } from "../render.jsx";


function Base({breadCrumbList, children, bottomDrawerParams, organizationIdRefreshCallback, showOrganizationSwitcher=true}) {
  const { direction, apiBaseUrl } = useAppContext();
  const [activeOrganizationId, setActiveOrganizationId] = useState(null);
  const drawerWidth = 250;
  const activeCrumbIndex = breadCrumbList.length - 1;

  window.React = React;
  window.ReactDom = ReactDom;
  window.MaterialUI = MaterialUI;

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
    <Box component="main"
      sx={{ flexGrow: 1, padding: {sm: 3, xs: 1, md: 5}, width: { md: `calc(100% - ${drawerWidth}px)` }, float: { md: direction === 'rtl' ? 'left' : 'right' } }}>
    <Grid container spacing={0} mt={{ xs: 10, md: 6 }} px={4}>
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
           color="text.secondary"
           href={href}
           sx={(theme) => ({
             fontSize: { xs: '0.78rem', sm: '0.84rem', md: '1.15rem' },
             lineHeight: 1.3,
             maxWidth: { xs: 110, sm: 180, md: 300 },
             whiteSpace: 'nowrap',
             overflow: 'hidden',
             textOverflow: 'ellipsis',
             transition: 'color 0.2s ease',
             '&:hover': {
               color: 'text.primary',
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
             maxWidth: { xs: 130, sm: 220, md: 360 },
             whiteSpace: 'nowrap',
             overflow: 'hidden',
             textOverflow: 'ellipsis',
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
        position: 'fixed',
        bottom: 0,
        right: direction === 'rtl' ? 'auto' : 2,
        left: direction === 'rtl' ? 2 : 'auto',
        padding: 1,
        zIndex: 1000,
        backgroundColor: 'transparent'
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: 'text.secondary',
          opacity: 0.8
        }}
      >
        Powered by{' '}
        <Link
          href="https://www.avacodesolutions.com/"
          target="_blank"
          rel="noopener noreferrer"
          sx={{
            color: 'primary.dark',
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
