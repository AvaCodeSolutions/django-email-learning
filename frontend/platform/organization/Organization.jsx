import { lazy, Suspense } from "react";
import Base from "../../src/components/Base";
import EmptyTableState from "../../src/components/EmptyTableState.jsx";
import Avatar from "@mui/material/Avatar";
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
import { Tabs, Tab, Link, Tooltip, Chip } from "@mui/material";
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import PeopleIcon from '@mui/icons-material/People';
import EmailIcon from '@mui/icons-material/Email';
import InfoIcon from '@mui/icons-material/Info';
import PublicIcon from '@mui/icons-material/Public';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import VpnKeyOutlinedIcon from '@mui/icons-material/VpnKeyOutlined';
import { useState, useEffect } from "react";
import apiClient from "../../src/apiClient.js";
import { Button } from "@mui/material";
import render, { useAppContext } from "../../src/render";
import { sanitizeEndpointUrl, sanitizeImageUrl, sanitizeUrl } from '../../src/sanitizeUrl.js';

const UserForm = lazy(() => import("./components/UserForm.jsx"));
const DeleteUserDialog = lazy(() => import("./components/DeleteUserDialog.jsx"));
const NewsletterForm = lazy(() => import("./components/NewsletterForm.jsx"));
const DeleteNewsletterDialog = lazy(() => import("./components/DeleteNewsletterDialog.jsx"));
const OrganizationForm = lazy(() => import("../organizations/components/OrganizationForm.jsx"));
const ApiKeyForm = lazy(() => import("./components/ApiKeyForm.jsx"));
const NewApiKeyDialog = lazy(() => import("./components/NewApiKeyDialog.jsx"));
const RevokeApiKeyDialog = lazy(() => import("./components/RevokeApiKeyDialog.jsx"));

const DEFAULT_TAB = 'general_info';

const apiKeyStatusOf = (apiKey) => {
    if (apiKey.revoked_at) return 'revoked';
    if (apiKey.expires_at && new Date(apiKey.expires_at) <= new Date()) return 'expired';
    return 'active';
};

function Organization() {
    const [organization, setOrganization] = useState(null);
    const [organizationUsers, setOrganizationUsers] = useState([]);
    const [newsletters, setNewsletters] = useState([]);
    const [apiKeys, setApiKeys] = useState([]);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogContent, setDialogContent] = useState(null);
    const [generalInfoEditable, setGeneralInfoEditable] = useState(false);
    const [generalInfoFormKey, setGeneralInfoFormKey] = useState(0);
    const [publicUrlCopied, setPublicUrlCopied] = useState(false);

    const { localeMessages, direction, userRole, isOrganizationAdmin, isPlatformAdmin, apiBaseUrl: rawApiBaseUrl, platformBaseUrl: rawPlatformBaseUrl, organizationId, currentUserId, availableFeatures = [] } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const platformBaseUrl = sanitizeUrl(rawPlatformBaseUrl);
    const canEditOrganization = isPlatformAdmin || isOrganizationAdmin;

    const newslettersEnabled = availableFeatures.includes('newsletters');
    const createNewsletterEnabled = availableFeatures.includes('create_newsletter');
    const organizationApiEnabled = availableFeatures.includes('organization_api');
    const canManageApiKeys = canEditOrganization && organizationApiEnabled;
    const [canAddMember, setCanAddMember] = useState(availableFeatures.includes('can_add_member'));

    // ?tab=<name> opens a specific tab on load; anything unknown - or a tab this
    // user cannot see - falls back to the default one.
    const availableTabs = [
        'general_info',
        'members',
        ...(newslettersEnabled ? ['newsletters'] : []),
        ...(canManageApiKeys ? ['api_keys'] : []),
    ];
    const [activeTab, setActiveTab] = useState(() => {
        const requestedTab = new URLSearchParams(window.location.search).get('tab');
        return availableTabs.includes(requestedTab) ? requestedTab : DEFAULT_TAB;
    });

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

    const refreshApiKeys = () => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/api-keys/`)
            .then(data => setApiKeys(data.api_keys))
            .catch(error => console.error('Error fetching API keys:', error));
    };

    useEffect(() => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/`)
            .then(data => setOrganization(data))
            .catch(error => console.error('Error fetching organization:', error));

        refreshUsers();

        if (newslettersEnabled) {
            refreshNewsletters();
        }

        if (canManageApiKeys) {
            refreshApiKeys();
        }
    }, []);

    const showDialog = (content) => {
        setDialogContent(content);
        setDialogOpen(true);
    };

    const closeDialog = () => setDialogOpen(false);

    const handleCopyPublicUrl = async () => {
        try {
            await navigator.clipboard.writeText(organization.public_url);
            setPublicUrlCopied(true);
            setTimeout(() => setPublicUrlCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy organization public URL:', error);
        }
    };

    return (
        <Base
            breadCrumbList={[
                { label: localeMessages["organizations"], href: `${platformBaseUrl}/organizations`, index: 0 },
                { label: organization ? organization.name : '', href: '#', index: 1 },
            ]}
            showOrganizationSwitcher={false}
        >
            <Grid size={12} sx={{ py: 2, px: { xs: 0, sm: 4 } }}>
                {organization && organization.is_public && organization.public_url && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mx: { xs: 2, sm: 0 }, mb: 1 }}>
                        <Box
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 0.5,
                                pl: 1.5,
                                pr: 0.5,
                                py: 0.2,
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 2,
                            }}
                        >
                            <Link
                                href={sanitizeUrl(organization.public_url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                underline="none"
                                sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 0.75,
                                    color: 'text.primary',
                                    fontSize: '0.8125rem',
                                    fontWeight: 500,
                                    '&:hover': { color: 'primary.dark' },
                                }}
                            >
                                <PublicIcon fontSize="small" />
                                {localeMessages["view_public_organization_page"]}
                            </Link>
                            <Tooltip title={publicUrlCopied ? localeMessages["public_organization_link_copied"] : localeMessages["copy_public_organization_link"]}>
                                <IconButton
                                    size="small"
                                    onClick={handleCopyPublicUrl}
                                    aria-label={localeMessages["copy_public_organization_link"]}
                                    sx={{
                                        borderRadius: '50%',
                                        border: '1px solid transparent',
                                        '&:hover': { borderColor: 'divider', color: 'primary.dark' },
                                    }}
                                >
                                    <ContentCopyIcon fontSize="small" />
                                </IconButton>
                            </Tooltip>
                        </Box>
                    </Box>
                )}
                <Box sx={{ backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', borderRadius: { xs: 0, sm: 2 }, minHeight: 300 }}>

                    <Tabs
                        value={activeTab}
                        onChange={(_, value) => setActiveTab(value)}
                        variant="scrollable"
                        scrollButtons="auto"
                        sx={{ borderBottom: 1, borderColor: 'divider' }}
                    >
                        <Tab
                            value="general_info"
                            icon={<InfoIcon fontSize="small" />}
                            iconPosition="start"
                            label={localeMessages["general_info"]}
                        />
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
                        {canManageApiKeys && (
                            <Tab
                                value="api_keys"
                                icon={<VpnKeyOutlinedIcon fontSize="small" />}
                                iconPosition="start"
                                label={localeMessages["api_keys"]}
                            />
                        )}
                    </Tabs>

                    <Box sx={{ p: { xs: 1, sm: 2 } }}>
                        {/* General info tab */}
                        {activeTab === 'general_info' && organization && (
                            <Box>
                                {canEditOrganization && !generalInfoEditable && (
                                    <Box sx={{ display: 'flex', justifyContent: direction === 'rtl' ? 'flex-start' : 'flex-end', mb: 1 }}>
                                        <Tooltip title={localeMessages["edit"]}>
                                            <Button
                                                variant="outlined"
                                                size="small"
                                                startIcon={<EditIcon fontSize="small" sx={{ marginLeft: direction === 'rtl' ? 1 : 0 }} />}
                                                onClick={() => setGeneralInfoEditable(true)}
                                            >
                                                {localeMessages["edit"]}
                                            </Button>
                                        </Tooltip>
                                    </Box>
                                )}
                                <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                    <OrganizationForm
                                        key={generalInfoFormKey}
                                        createMode={false}
                                        readOnly={!canEditOrganization || !generalInfoEditable}
                                        organizationId={organizationId}
                                        initialName={organization.name}
                                        initialDescription={organization.description}
                                        initialLogoUrl={organization.logo}
                                        initialLogoPath={organization.logo_path}
                                        initialSocialLinks={organization.social_links}
                                        initialIsPublic={organization.is_public}
                                        initialBrandColor={organization.brand_color}
                                        successCallback={(data) => {
                                            setOrganization(data);
                                            setGeneralInfoEditable(false);
                                            setGeneralInfoFormKey((key) => key + 1);
                                        }}
                                        failureCallback={(error) => console.error('Error updating organization:', error)}
                                        cancelCallback={() => {
                                            setGeneralInfoEditable(false);
                                            setGeneralInfoFormKey((key) => key + 1);
                                        }}
                                    />
                                </Suspense>
                            </Box>
                        )}

                        {/* Members tab */}
                        {activeTab === 'members' && (
                            <>
                                <Tooltip title={canAddMember ? '' : localeMessages["cannot_add_member"]}>
                                <span>
                                <Button
                                    variant="contained"
                                    color="secondary"
                                    disabled={!canAddMember}
                                    onClick={() => showDialog(
                                        <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                            <UserForm
                                                organizationId={organizationId}
                                                onClose={closeDialog}
                                                refreshUsers={refreshUsers}
                                                onCreateSuccess={(data) => {
                                                    if (data?.can_add_member !== undefined) {
                                                        setCanAddMember(data.can_add_member);
                                                    }
                                                }}
                                            />
                                        </Suspense>
                                    )}
                                >
                                    {localeMessages["add_user"]}
                                </Button>
                                </span>
                                </Tooltip>
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
                                                            <TableCell>
                                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
                                                                    <Avatar
                                                                        src={sanitizeImageUrl(user.photo_url)}
                                                                        sx={(theme) => ({
                                                                            width: 30,
                                                                            height: 30,
                                                                            fontSize: '0.85rem',
                                                                            fontWeight: 600,
                                                                            color: '#fff',
                                                                            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.deepPurple[400]} 100%)`,
                                                                        })}
                                                                    >
                                                                        {(user.email?.[0] || '?').toUpperCase()}
                                                                    </Avatar>
                                                                    <Typography component="span">{user.email}</Typography>
                                                                </Box>
                                                            </TableCell>
                                                            <TableCell>{user.role}</TableCell>
                                                            {userRole !== 'viewer' && (() => {
                                                                const isSelf = user.user_id === currentUserId;
                                                                return (
                                                                <TableCell align={direction === 'rtl' ? 'left' : 'right'}>
                                                                    <IconButton onClick={() => showDialog(
                                                                        <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                                            <UserForm organizationId={organizationId} onClose={closeDialog} refreshUsers={refreshUsers} user={user} disableRoleField={isSelf} />
                                                                        </Suspense>
                                                                    )}>
                                                                        <EditIcon fontSize="small" />
                                                                    </IconButton>
                                                                    <Tooltip title={isSelf ? localeMessages["cannot_remove_self"] : ''}>
                                                                        <span>
                                                                            <IconButton
                                                                                disabled={isSelf}
                                                                                aria-label={`Delete ${user.email}`}
                                                                                onClick={() => showDialog(
                                                                                    <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                                                        <DeleteUserDialog user={user} handleClose={closeDialog} handleSuccess={() => { refreshUsers(); closeDialog(); }} />
                                                                                    </Suspense>
                                                                                )}
                                                                            >
                                                                                <DeleteIcon fontSize="small" />
                                                                            </IconButton>
                                                                        </span>
                                                                    </Tooltip>
                                                                </TableCell>
                                                                );
                                                            })()}
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
                                {createNewsletterEnabled && isOrganizationAdmin && (
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

                        {/* API keys tab */}
                        {canManageApiKeys && activeTab === 'api_keys' && (
                            <>
                                <Typography variant="body2" sx={{ mb: 2 }}>{localeMessages["api_keys_intro"]}</Typography>
                                <Button
                                    variant="contained"
                                    color="secondary"
                                    onClick={() => showDialog(
                                        <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                            <ApiKeyForm
                                                organizationId={organizationId}
                                                onClose={closeDialog}
                                                onCreated={(created) => showDialog(
                                                    <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                        <NewApiKeyDialog
                                                            token={created.token}
                                                            onClose={() => { refreshApiKeys(); closeDialog(); }}
                                                        />
                                                    </Suspense>
                                                )}
                                            />
                                        </Suspense>
                                    )}
                                >
                                    {localeMessages["create_api_key"]}
                                </Button>
                                <Box sx={{ mt: 2, width: '100%' }}>
                                    <TableContainer>
                                        <Table>
                                            <TableHead>
                                                <TableRow>
                                                    <TableCell>{localeMessages["api_key_name"]}</TableCell>
                                                    <TableCell>{localeMessages["key_id"]}</TableCell>
                                                    <TableCell>{localeMessages["api_key_scopes"]}</TableCell>
                                                    <TableCell>{localeMessages["status"]}</TableCell>
                                                    <TableCell>{localeMessages["created_by"]}</TableCell>
                                                    <TableCell>{localeMessages["created_at"]}</TableCell>
                                                    <TableCell>{localeMessages["last_used"]}</TableCell>
                                                    <TableCell align={direction === 'rtl' ? 'left' : 'right'}>{localeMessages["actions"]}</TableCell>
                                                </TableRow>
                                            </TableHead>
                                            <TableBody>
                                                {apiKeys.length === 0 && (
                                                    <EmptyTableState
                                                        colSpan={8}
                                                        message={localeMessages["no_api_keys"]}
                                                    />
                                                )}
                                                {apiKeys.map((apiKey) => {
                                                    const status = apiKeyStatusOf(apiKey);
                                                    return (
                                                        <TableRow key={apiKey.id}>
                                                            <TableCell>{apiKey.name}</TableCell>
                                                            <TableCell>
                                                                {/* The public half of the token. The secret is
                                                                    hashed and is never returned by the listing. */}
                                                                <Typography component="span" sx={{ fontFamily: 'monospace', overflowWrap: 'anywhere' }}>
                                                                    {apiKey.key_id}
                                                                </Typography>
                                                            </TableCell>
                                                            <TableCell>
                                                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                                                    {apiKey.scopes.map(scope => (
                                                                        <Chip key={scope} size="small" variant="outlined" label={scope} />
                                                                    ))}
                                                                </Box>
                                                            </TableCell>
                                                            <TableCell>
                                                                <Chip
                                                                    size="small"
                                                                    label={localeMessages[status]}
                                                                    color={status === 'active' ? 'success' : 'default'}
                                                                    variant={status === 'active' ? 'filled' : 'outlined'}
                                                                />
                                                            </TableCell>
                                                            <TableCell>{apiKey.created_by}</TableCell>
                                                            <TableCell>{apiKey.created_at}</TableCell>
                                                            <TableCell>{apiKey.last_used_at || localeMessages["never_used"]}</TableCell>
                                                            <TableCell align={direction === 'rtl' ? 'left' : 'right'}>
                                                                {status !== 'revoked' && (
                                                                    <IconButton
                                                                        aria-label={`Revoke ${apiKey.name}`}
                                                                        onClick={() => showDialog(
                                                                            <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                                                                                <RevokeApiKeyDialog
                                                                                    apiKey={apiKey}
                                                                                    organizationId={organizationId}
                                                                                    onClose={closeDialog}
                                                                                    onSuccess={refreshApiKeys}
                                                                                />
                                                                            </Suspense>
                                                                        )}
                                                                    >
                                                                        <DeleteIcon fontSize="small" />
                                                                    </IconButton>
                                                                )}
                                                            </TableCell>
                                                        </TableRow>
                                                    );
                                                })}
                                            </TableBody>
                                        </Table>
                                    </TableContainer>
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

export default Organization;
