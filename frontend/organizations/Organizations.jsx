import Base from "../src/components/Base";
import { Box, Button, Dialog, Grid } from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import { useState } from "react";
import render from "../src/render";
import OrganizationForm from "./components/OrganizationForm";

function Organizations() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogContent, setDialogContent] = useState(null);

  const handleOrganizationCreated = (data) => {
    console.log('Organization created successfully:', data);
    setDialogOpen(false);
  };

  const handleOrganizationCreationFailed = (error) => {
    console.error('Error creating organization:', error);
  };

  return (
    <Base breadCrumbList={[{label: 'Organizations', href: '#'}]} showOrganizationSwitcher={false}>
      <Grid size={12} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300 }}>
        <Button variant="outlined" startIcon={<AddIcon />} sx={{ marginBottom: 2 }} onClick={() => {
          setDialogContent(<OrganizationForm
            successCallback={handleOrganizationCreated}
            failureCallback={handleOrganizationCreationFailed}
            cancelCallback={() => setDialogOpen(false)}
            createMode={true}
          />);
          setDialogOpen(true);
        }}>Add an Organization</Button>
        </Box>
      </Grid>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>
    </Base>)
}

render({children: <Organizations />});
