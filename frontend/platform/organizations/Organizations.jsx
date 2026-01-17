import Base from "../../src/components/Base";
import { Box, Button, Dialog, Grid, IconButton, TableContainer, Table, TableHead, TableRow,TableBody, TableCell } from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import PublicIcon from '@mui/icons-material/Public';
import { useState, useEffect, use } from "react";
import { getCookie } from "../../src/utils";
import render from "../../src/render";
import OrganizationForm from "./components/OrganizationForm";

function Organizations() {
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

  const apiBaseUrl = localStorage.getItem('apiBaseUrl');

  const handleOrganizationCreated = (data) => {
    console.log('Organization created successfully:', data);
    setDialogOpen(false);
    setTableUpdates(prev => [...prev, data]);
  };

  const handleOrganizationCreationFailed = (error) => {
    console.error('Error creating organization:', error);
  };

  return (
    <Base breadCrumbList={[{label: 'Organizations', href: '#'}]} showOrganizationSwitcher={false}>
      <Grid size={12} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300 }}>
        <Button variant="contained" startIcon={<AddIcon />} sx={{ marginBottom: 2 }} onClick={() => {
          setDialogContent(<OrganizationForm
            successCallback={handleOrganizationCreated}
            failureCallback={handleOrganizationCreationFailed}
            cancelCallback={() => setDialogOpen(false)}
            createMode={true}
          />);
          setDialogOpen(true);
        }}>Add an Organization</Button>

        { organizations.length > 0 && (<TableContainer sx={{ maxHeight: 440, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Public URL</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              { organizations.map((org) => (
                <TableRow key={org.id}>
                  <TableCell>{org.name}</TableCell>
                  <TableCell><a href={org.public_url}><IconButton><PublicIcon fontSize="small"/></IconButton></a></TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>)}

        </Box>

      </Grid>



      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>
    </Base>)
}

render({children: <Organizations />});
