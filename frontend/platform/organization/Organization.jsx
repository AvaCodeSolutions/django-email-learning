import { lazy, Suspense } from "react";
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
import { Tabs, Tab, Link } from "@mui/material";
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import PeopleIcon from '@mui/icons-material/People';
import EmailIcon from '@mui/icons-material/Email';
import { useState, useEffect } from "react";
import apiClient from "../../src/apiClient.js";
import { Button } from "@mui/material";
import render, { useAppContext } from "../../src/render";

const UserForm = lazy(() => import("./components/UserForm.jsx"));
const DeleteUserDialog = lazy(() => import("./components/DeleteUserDialog.jsx"));
const NewsletterForm = lazy(() => import("./components/NewsletterForm.jsx"));
const DeleteNewsletterDialog = lazy(() => import("./components/DeleteNewsletterDialog.jsx"));

function Organization() {
    const [organization, setOrganization] = useState(null);
    const [organizationUsers, setOrganizationUsers] = useState([]);
    const [newsletters, setNewsletters] = useState([]);
    const initialTab = new URLSearchParams(window.location.search).get('tab') || 'members';
    const [activeTab, setActiveTab] = useState(initialTab);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogContent, setDialogContent] = useState(null);

    const { localeMessages, direction, userRole, isOrganizationAdmin, apiBaseUrl, platformBaseUrl, organizationId, availableFeatures = [] } = useAppContext();

    const newslettersEnabled = availableFeatures.includes('newsletters');

    const refreshUsers = () => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/users/`)
            .then(data => setOrganizationUsers(data.organization_users))
            .catch(error => console.error('Error fetching organization users:', error));
    };

    const refreshNewsletters = () => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/newsletters/`)
            .then(data => setNewsletters(data.newsletters))
            .catch(error => console.error('Error fetching newsletters:', error));
    };

    useEffect(() => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/`)
            .then(data => setOrganization(data))
            .catch(error => console.error('Error fetching organization:', error));

        refreshUsers();

        if (newslettersEnabled) {
            refreshNewsletters();
        }
    }, []);

    const showDialog = (content) => {
        setDialogContent(content);
        setDialogOpen(true);
    };

    const closeDialog = () => setDialogOpen(false);

    return (
        <Base
            breadCrumbList={[
                { label: localeMessages["organizations"], href: `${platformBaseUrl}/organizations`, index: 0 },
                { label: organization ? organization.name : '', href: '#', index: 1 },
            ]}
            showOrganizationSwitcher={false}
        >
            <Grid size={12} sx={{ py: 2, px: { xs: 0, sm: 4 } }}>
                <Box sx={{ backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', borderRadius: { xs: 0, sm: 2 }, minHeight: 300 }}>

                    <Tabs
                        value={activeTab}
                        onChange={(_, value) => setActiveTab(value)}
                        variant="scrollable"
                        scrollButtons="auto"
                        sx={{ borderBottom: 1, borderColor: 'divider' }}
                    >
                        <Tab
                            value="members"
                            icon={<PeopleIcon fontSize="small" />}
                            iconPosition="start"
                            label={localeMessages["members"]}
                        />
                        {newslettersEnabled && (
                            <Tab
                                value="newsletters"
                                icon={<EmailIcon fontSize="small" />}
                                iconPosition="start"
                                label={localeMessages["newsletters"]}
                            />
                        )}
                    </Tabs>

                    <Box sx={{ p: { xs: 1, sm: 2 } }}>
                        {/* Members tab */}
                        {activeTab === 'members' && (
                            <>
                                <Button
                                    variant="contained"
                                    color="secondary"
                                    onClick={() => showDialog(
                                        <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                            <UserForm organizationId={organizationId} onClose={closeDialog} refreshUsers={refreshUsers} />
                                        </Suspense>
                                    )}
                                >
                                    {localeMessages["add_user"]}
                                </Button>
                                <Box sx={{ mt: 2, width: '100%' }}>
                                    {organizationUsers.length > 0 ? (
                                        <TableContainer>
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
                                                            {userRole !== 'viewer' && (
                                                                <TableCell align={direction === 'rtl' ? 'left' : 'right'}>
                                                                    <IconButton onClick={() => showDialog(
                                                                        <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                                            <UserForm organizationId={organizationId} onClose={closeDialog} refreshUsers={refreshUsers} user={user} />
                                                                        </Suspense>
                                                                    )}>
                                                                        <EditIcon fontSize="small" />
                                                                    </IconButton>
                                                                    <IconButton
                                                                        aria-label={`Delete ${user.email}`}
                                                                        onClick={() => showDialog(
                                                                            <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                                                <DeleteUserDialog user={user} handleClose={closeDialog} handleSuccess={() => { refreshUsers(); closeDialog(); }} />
                                                                            </Suspense>
                                                                        )}
                                                                    >
                                                                        <DeleteIcon fontSize="small" />
                                                                    </IconButton>
                                                                </TableCell>
                                                            )}
                                                        </TableRow>
                                                    ))}
                                                </TableBody>
                                            </Table>
                                        </TableContainer>
                                    ) : (
                                        <Typography variant="body1">{localeMessages["no_users_in_organization"]}</Typography>
                                    )}
                                </Box>
                            </>
                        )}

                        {/* Newsletters tab */}
                        {newslettersEnabled && activeTab === 'newsletters' && (
                            <>
                                {isOrganizationAdmin && (
                                    <Button
                                        variant="contained"
                                        color="secondary"
                                        onClick={() => showDialog(
                                            <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                <NewsletterForm organizationId={organizationId} onClose={closeDialog} refreshNewsletters={refreshNewsletters} />
                                            </Suspense>
                                        )}
                                    >
                                        {localeMessages["create_newsletter"]}
                                    </Button>
                                )}
                                <Box sx={{ mt: 2, width: '100%' }}>
                                    {newsletters.length > 0 ? (
                                        <TableContainer>
                                            <Table>
                                                <TableHead>
                                                    <TableRow>
                                                        <TableCell>{localeMessages["newsletter_title"]}</TableCell>
                                                        <TableCell>{localeMessages["newsletter_language"]}</TableCell>
                                                        <TableCell>{localeMessages["newsletter_subscribers"]}</TableCell>
                                                        {isOrganizationAdmin && <TableCell align={direction === 'rtl' ? 'left' : 'right'}>{localeMessages["actions"]}</TableCell>}
                                                    </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                    {newsletters.map((nl) => (
                                                        <TableRow key={nl.id}>
                                                            <TableCell>
                                                                <Link href={`${platformBaseUrl}/organizations/${organizationId}/newsletters/${nl.id}/`} color="secondary.dark">{nl.title}</Link>
                                                            </TableCell>
                                                            <TableCell>{nl.language}</TableCell>
                                                            <TableCell>{nl.subscriber_count}</TableCell>
                                                            {isOrganizationAdmin && (
                                                                <TableCell align={direction === 'rtl' ? 'left' : 'right'}>
                                                                    <IconButton
                                                                        aria-label={`Delete ${nl.title}`}
                                                                        onClick={() => showDialog(
                                                                            <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                                                <DeleteNewsletterDialog newsletter={nl} onClose={closeDialog} onSuccess={refreshNewsletters} />
                                                                            </Suspense>
                                                                        )}
                                                                    >
                                                                        <DeleteIcon fontSize="small" />
                                                                    </IconButton>
                                                                </TableCell>
                                                            )}
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
                </Box>
            </Grid>

            <Dialog open={dialogOpen} onClose={closeDialog} fullWidth maxWidth="sm">
                {dialogContent}
            </Dialog>
        </Base>
    );
}

render({ children: <Organization /> });
