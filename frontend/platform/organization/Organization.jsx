import { lazy, Suspense } from "react";
import Base from "../../src/components/Base";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
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
const NewsletterForm = lazy(() => import("./components/NewsletterForm.jsx"));

function Organization() {
    const [organization, setOrganization] = useState(null);
    const [organizationUsers, setOrganizationUsers] = useState([]);
    const [newsletters, setNewsletters] = useState([]);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogContent, setDialogContent] = useState(null);

    const { localeMessages, direction, userRole, apiBaseUrl, platformBaseUrl, organizationId, availableFeatures = [] } = useAppContext();

    const newslettersEnabled = availableFeatures.includes('newsletters');

    const refreshUsers = () => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/users/`)
        .then(data => {
            setOrganizationUsers(data.organization_users);
        })
        .catch(error => {
            console.error('Error fetching organization users:', error);
        });
    };

    const refreshNewsletters = () => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/newsletters/`)
        .then(data => {
            setNewsletters(data.newsletters);
        })
        .catch(error => {
            console.error('Error fetching newsletters:', error);
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

        if (newslettersEnabled) {
            refreshNewsletters();
        }
    }, []);

    const showEditUserDialog = (user) => {
        setDialogContent(
            <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                <UserForm organizationId={organizationId} onClose={() => setDialogOpen(false)} refreshUsers={refreshUsers} user={user} />
            </Suspense>
        );
        setDialogOpen(true);
    };

    const showCreateNewsletterDialog = () => {
        setDialogContent(
            <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                <NewsletterForm organizationId={organizationId} onClose={() => setDialogOpen(false)} refreshNewsletters={refreshNewsletters} />
            </Suspense>
        );
        setDialogOpen(true);
    };

    return (<Base breadCrumbList={[
        {label: localeMessages["organizations"], href: `${platformBaseUrl}/organizations`, index: 0},
        {label: organization ? organization.name : '', href: '#', index: 1}]} showOrganizationSwitcher={false}>
        <Grid size={12} sx={{ py: 2, px: { xs: 0, sm: 4 } }}>
            <Box sx={{ p: { xs: 1, sm: 2 }, backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', borderRadius: { xs: 0, sm: 2 }, minHeight: 300 }}>

                {/* Users section */}
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

                {/* Newsletters section */}
                {newslettersEnabled && (
                    <>
                        <Divider sx={{ my: 3 }} />
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                            <Typography variant="h6">{localeMessages["newsletters"]}</Typography>
                            {userRole === 'admin' && (
                                <Button variant="contained" color="secondary" onClick={showCreateNewsletterDialog}>
                                    {localeMessages["create_newsletter"]}
                                </Button>
                            )}
                        </Box>
                        <Box sx={{ width: '100%' }}>
                            {newsletters.length > 0 ? (
                                <TableContainer>
                                    <Table>
                                        <TableHead>
                                            <TableRow>
                                                <TableCell>{localeMessages["newsletter_title"]}</TableCell>
                                                <TableCell>{localeMessages["newsletter_language"]}</TableCell>
                                                <TableCell>{localeMessages["newsletter_subscribers"]}</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {newsletters.map((nl) => (
                                                <TableRow key={nl.id}>
                                                    <TableCell>{nl.title}</TableCell>
                                                    <TableCell>{nl.language}</TableCell>
                                                    <TableCell>{nl.subscriber_count}</TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            ) : (
                                <Typography variant="body1">{localeMessages["no_newsletters"]}</Typography>
                            )}
                        </Box>
                    </>
                )}
            </Box>
        </Grid>
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
            {dialogContent}
        </Dialog>
    </Base>);
}

render({children: <Organization />});
