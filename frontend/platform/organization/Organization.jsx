import render from "../../src/render";
import { lazy, Suspense, use } from "react";
import Base from "../../src/components/Base";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import TableContainer from "@mui/material/TableContainer";
import Table from "@mui/material/Table";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import Typography from "@mui/material/Typography";
import LinearProgress from "@mui/material/LinearProgress";
import Dialog from "@mui/material/Dialog";
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { getCookie } from "../../src/utils.js";
import { useState, useEffect } from "react";
import { Button } from "@mui/material";

const UserForm = lazy(() => import("./components/UserForm.jsx"));
const DeleteUserDialog = lazy(() => import("./components/DeleteUserDialog.jsx"));
const platformBaseUrl = localStorage.getItem('platformBaseUrl');
const apiBaseUrl = localStorage.getItem('apiBaseUrl');
const userRole = localStorage.getItem('userRole');

function Organization() {
    const [organization, setOrganization] = useState(null);
    const [organizationUsers, setOrganizationUsers] = useState([]);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogContent, setDialogContent] = useState(null);

    const refreshUsers = () => {
        fetch(`${apiBaseUrl}/organizations/${organizationId}/users/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
        .then(data => {
            setOrganizationUsers(data.organization_users);
        })
        .catch(error => {
            console.error('Error fetching organization users:', error);
        });
    };

    useEffect(() => {

        fetch(`${apiBaseUrl}/organizations/${organizationId}/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
        .then(data => {
            setOrganization(data);
        })
        .catch(error => {
            console.error('Error fetching organization:', error);
        });

        refreshUsers();
    }, []);

    const showEditUserDialog = (user) => {
        setDialogContent(
            <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                <UserForm organizationId={organizationId} onClose={() => setDialogOpen(false)} refreshUsers={refreshUsers} user={user} />
            </Suspense>
        );
        setDialogOpen(true);
    };

    return (<Base breadCrumbList={[
        {label: localeMessages["organizations"], href: `${platformBaseUrl}/organizations`, index: 0},
        {label: organization ? organization.name : '', href: '#', index: 1}]} showOrganizationSwitcher={false}>
        <Grid size={12} py={2} px={4} container sx={{borderColor: 'grey.300', borderRadius: 1, borderWidth: 1, borderStyle: 'solid', mt: 2}}>
            <Button variant="contained" color="primary" onClick={() => {setDialogContent(
                <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                    <UserForm organizationId={organizationId} onClose={() => setDialogOpen(false)} refreshUsers={refreshUsers} />
                 </Suspense>
             ); setDialogOpen(true); }}>
                {localeMessages["add_user"]}
            </Button>
            <Box sx={{ p: 2, mt: 2, borderRadius: 1, bgcolor: "background.paper", width: '100%' }}>
                { organizationUsers.length > 0 ? <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>{localeMessages["user"]}</TableCell>
                                <TableCell>{localeMessages["role"]}</TableCell>
                                {userRole !== 'viewer' && <TableCell align={direction === 'rtl' ? 'left' : 'right'}>{localeMessages["actions"]}</TableCell>}
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {organizationUsers.map((user) => (
                                <TableRow key={user.user_id}>
                                    <TableCell>{user.email}</TableCell>
                                    <TableCell>{user.role}</TableCell>
                                    {userRole !== 'viewer' && <TableCell align={direction === 'rtl' ? 'left' : 'right'}>
                                        <IconButton onClick={() => {
                                            showEditUserDialog(user);}}><EditIcon fontSize="small" /></IconButton>
                                        <IconButton aria-label={`Delete ${user.email}`} onClick={() => {
                                            setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                <DeleteUserDialog user={user} handleClose={() => setDialogOpen(false)} handleSuccess={() => { refreshUsers(); setDialogOpen(false); }} />
                                             </Suspense>);
                                        setDialogOpen(true);
                                        }}><DeleteIcon fontSize="small" /></IconButton>
                                    </TableCell>}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer> : <Typography variant="body1">{localeMessages["no_users_in_organization"]}</Typography> }
            </Box>
      </Grid>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>
    </Base>);
}

render({children: <Organization />});
