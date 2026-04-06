import Base from "../../src/components/Base";
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Dialog from "@mui/material/Dialog"
import Grid from "@mui/material/Grid"
import IconButton from "@mui/material/IconButton"
import LinearProgress from "@mui/material/LinearProgress"
import Link from "@mui/material/Link"
import Paper from "@mui/material/Paper"
import TableContainer from "@mui/material/TableContainer"
import Table from "@mui/material/Table"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import Typography from "@mui/material/Typography"
import AddIcon from '@mui/icons-material/Add';
import PublicIcon from '@mui/icons-material/Public';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { useState, useEffect, use } from "react";
import { getCookie } from "../../src/utils";
import render, { useAppContext } from "../../src/render";
import { lazy, Suspense } from "react";

const OrganizationForm = lazy(() => import("./components/OrganizationForm.jsx"));

function Organizations() {
  const { localeMessages, direction, apiBaseUrl, platformBaseUrl, isPlatformAdmin } = useAppContext();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogContent, setDialogContent] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const [tableUpdates, setTableUpdates] = useState([]);

  useEffect(() => {
    fetch(`${apiBaseUrl}/organizations/`, {
      method: 'GET',
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
  }, [tableUpdates]);

  const handleSuccessFormSubmission = (data) => {
    console.log('Organization created successfully:', data);
    setDialogOpen(false);
    setTableUpdates(prev => [...prev, data]);
  };

  const handleFailedFormSubmission = (error) => {
    console.error('Error creating organization:', error);
  };

  const goToUrl = (url) => {
    window.open(url, '_blank');
  }

  const deleteOrganization = (organizationId) => {
    fetch(`${apiBaseUrl}/organizations/${organizationId}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
    .then(response => {
      if (response.ok) {
        console.log('Organization deleted successfully');
        setTableUpdates(prev => [...prev, { deletedOrganizationId: organizationId }]);
      } else {
        console.error('Error deleting organization');
      }
    })
    .catch(error => {
      console.error('Error deleting organization:', error);
    });
  }

  const htmlTag = document.getElementsByTagName("html")[0];

  const deleteConfirmationDialog = (organization) => {
    setDialogContent(
      <Box sx={{ p: 2 }}>
        <Typography variant="h6">{localeMessages["confirm_deletion"]}</Typography>
        <Alert severity="warning" variant="outlined" sx={{ mt: 1 }}>{localeMessages["are_you_sure_delete_org"].replace("ORGANIZATION_NAME", organization.name)}</Alert>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
          <Button onClick={() => setDialogOpen(false)} sx={{ mr: 1 }}>{localeMessages["cancel"]}</Button>
          <Button variant="contained" color="error" onClick={() => {
            deleteOrganization(organization.id);
            setDialogOpen(false);
          }}>{localeMessages["delete"]}</Button>
        </Box>
      </Box>
    );
    setDialogOpen(true);
  }

  return (
    <Base breadCrumbList={[{label: localeMessages["organizations"], href: '#'}]} showOrganizationSwitcher={false}>
      <Grid size={12} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'border.main', backgroundColor: 'background.box', borderRadius: 2, minHeight: 300 }}>
        {isPlatformAdmin && <Button variant="contained" startIcon={<AddIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2 }} onClick={() => {
          setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><OrganizationForm
            successCallback={handleSuccessFormSubmission}
            failureCallback={handleFailedFormSubmission}
            cancelCallback={() => setDialogOpen(false)}
            createMode={true}
          /></Suspense>);
          setDialogOpen(true);
        }}>{localeMessages["add_organization"]}</Button>}

        { organizations.length > 0 && (<TableContainer component={Paper} sx={{ maxHeight: 440, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell dir={htmlTag.dir} sx={{ textAlign: htmlTag.dir === 'rtl' ? 'right' : 'left' }}>{localeMessages["name"]}</TableCell>
                <TableCell sx={{ width: '150px' }}>{localeMessages["actions"]}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              { organizations.map((org) => (
                <TableRow key={org.id}>
                  <TableCell dir={htmlTag.dir} sx={{ textAlign: htmlTag.dir === 'rtl' ? 'right' : 'left' }}><Link color='secondary.dark' href={`${platformBaseUrl}/organizations/${org.id}/`}>{org.name}</Link></TableCell>
                  <TableCell>
                    <IconButton onClick={() => goToUrl(org.public_url)}><PublicIcon fontSize="small"/></IconButton>
                    { isPlatformAdmin && <><IconButton onClick={() => {
                      setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><OrganizationForm
                        successCallback={handleSuccessFormSubmission}
                        failureCallback={handleFailedFormSubmission}
                        cancelCallback={() => setDialogOpen(false)}
                        createMode={false}
                        initialName={org.name}
                        initialDescription={org.description}
                        initialLogoUrl={org.logo}
                        initialWebsite={org.website}
                        initialLinkedinPage={org.linkedin_page}
                        initialYoutubeChannel={org.youtube_channel}
                        organizationId={org.id}
                      /></Suspense>);
                      setDialogOpen(true);
                    }}><EditIcon fontSize="small"/></IconButton>
                    <IconButton onClick={() => deleteConfirmationDialog(org)}><DeleteIcon fontSize="small" /></IconButton></>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </TableContainer>

        )}

        </Box>

      </Grid>



      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>
    </Base>)
}

render({children: <Organizations />});
