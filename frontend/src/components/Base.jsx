import BottomDrawer from "./BottomDrawer";
import MenuBar from "./MenuBar";
import { useState, useEffect } from "react";
import { Grid, Breadcrumbs, Typography, Link } from "@mui/material";
import { getCookie } from "../utils.js";

import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

function Base({breadCrumbList, children, bottomDrawerParams, organizationIdRefreshCallback, showOrganizationSwitcher=true}) {
  const [activeOrganizationId, setActiveOrganizationId] = useState(null);
  const baseApiUrl = localStorage.getItem('apiBaseUrl');

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
    <MenuBar activeOrganizationId={activeOrganizationId} changeOrganizationCallback={setActiveOrganizationId} showOrganizationSwitcher={showOrganizationSwitcher} />
    <Grid container spacing={0} mt={10} px={4}>
      <Grid size={{xs: 12}}>
      <Breadcrumbs aria-label="breadcrumb">
       { breadCrumbList.map(({label, href, index}) => (
         index < breadCrumbList.length - 1 ?
         <Link key={index} underline="hover" color="inherit" href={href}>
           {label}
         </Link> :
         <Typography key={index} sx={{ color: 'text.primary', fontSize: { xs: 12, sm: 14 } }}>
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
    </>
  );
}

export default Base;
