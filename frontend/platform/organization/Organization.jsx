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
import { useState, useEffect } from "react";
import apiClient from "../../src/apiClient.js";
import { Button } from "@mui/material";
import render, { useAppContext } from "../../src/render";

const UserForm = lazy(() => import("./components/UserForm.jsx"));
const DeleteUserDialog = lazy(() => import("./components/DeleteUserDialog.jsx"));

function Organization() {
    const [organization, setOrganization] = useState(null);
    const [organizationUsers, setOrganizationUsers] = useState([]);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogContent, setDialogContent] = useState(null);

    const { localeMessages, direction, userRole, apiBaseUrl, platformBaseUrl, organizationId } = useAppContext();

    const refreshUsers = () => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/users/`)
        .then(data => {
            setOrganizationUsers(data.organization_users);
        })
        .catch(error => {
            console.error('Error fetching organization users:', error);
        });
    };

    useEffect(() => {

        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/`)
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
        <Grid size={12} sx={{ py: 2, px: { xs: 0, sm: 4 } }}>
            <Box sx={{ p: { xs: 1, sm: 2 }, borderTop: '1px solid', borderBottom: '1px solid', borderLeft: { xs: 'none', sm: '1px solid' }, borderRight: { xs: 'none', sm: '1px solid' }, borderColor: 'border.main', backgroundColor: 'background.box', borderRadius: { xs: 0, sm: 2 }, minHeight: 300 }}>
                <Button variant="contained" color="secondary" onClick={() => {setDialogContent(
                    <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                        <UserForm organizationId={organizationId} onClose={() => setDialogOpen(false)} refreshUsers={refreshUsers} />
                    </Suspense>
                ); setDialogOpen(true); }}>
                    {localeMessages["add_user"]}
                </Button>
                <Box sx={{ mt: 2, width: '100%' }}>
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
            </Box>
                </Grid>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>
    </Base>);
}

render({children: <Organization />});
