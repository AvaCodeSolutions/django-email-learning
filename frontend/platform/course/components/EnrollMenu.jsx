import { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../../../src/render.jsx';
import PersonAddAlt1Icon from '@mui/icons-material/PersonAddAlt1';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import GoogleIcon from '@mui/icons-material/Google';
import { Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Menu, MenuItem, Alert, Typography, FormGroup, FormControlLabel, Checkbox } from '@mui/material';
import apiClient from '../../../src/apiClient.js';


const EnrollMenu = ({successCallback}) => {
    const {courseId, localeMessages, direction, apiBaseUrl, userRole, availableFeatures = [] } = useAppContext();
    const [enrollMenuAnchorEl, setEnrollMenuAnchorEl] = useState(null);
    const [manualEnrollOpen, setManualEnrollOpen] = useState(false);
    const [googleWorkspaceDialogOpen, setGoogleWorkspaceDialogOpen] = useState(false);
    const [googleAuthSubmitting, setGoogleAuthSubmitting] = useState(false);
    const [googleAuthError, setGoogleAuthError] = useState('');
    const [googleAuthorizationUrl, setGoogleAuthorizationUrl] = useState('');
    const [googleAuthSessionId, setGoogleAuthSessionId] = useState(null);
    const [googleGroupsDialogOpen, setGoogleGroupsDialogOpen] = useState(false);
    const [googleGroups, setGoogleGroups] = useState([]);
    const [selectedGroups, setSelectedGroups] = useState(['all']);
    const [googleGroupsError, setGoogleGroupsError] = useState('');
    const [manualEnrollEmail, setManualEnrollEmail] = useState('');
    const [manualEnrollError, setManualEnrollError] = useState('');
    const [manualEnrollSubmitting, setManualEnrollSubmitting] = useState(false);
    const manualEnrollInputRef = useRef(null);
    const enrollMenuListRef = useRef(null);

    const organizationId = localStorage.getItem('activeOrganizationId');

    useEffect(() => {
        if (manualEnrollOpen && manualEnrollInputRef.current) {
            manualEnrollInputRef.current.focus();
        }
    }, [manualEnrollOpen]);

    const isEnrollMenuOpen = Boolean(enrollMenuAnchorEl);

    const openEnrollMenu = (event) => {
        setEnrollMenuAnchorEl(event.currentTarget);
    }

    const closeEnrollMenu = () => {
        setEnrollMenuAnchorEl(null);
    }

    const handleEnrollMenuKeyDown = (event) => {
        if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') {
            return;
        }

        const menuItems = enrollMenuListRef.current?.querySelectorAll('[role="menuitem"]:not([aria-disabled="true"])');
        if (!menuItems || menuItems.length === 0) {
            return;
        }

        event.preventDefault();

        const items = Array.from(menuItems);
        const currentIndex = items.findIndex((item) => item === document.activeElement);
        const directionStep = event.key === 'ArrowDown' ? 1 : -1;
        const fallbackIndex = directionStep === 1 ? 0 : items.length - 1;
        const nextIndex = currentIndex === -1
            ? fallbackIndex
            : (currentIndex + directionStep + items.length) % items.length;

        items[nextIndex].focus();
    }

    const openManualEnrollDialog = () => {
        closeEnrollMenu();
        setManualEnrollError('');
        setManualEnrollEmail('');
        setManualEnrollOpen(true);
    }

    const createGoogleOAuthSession = async () => {
        setGoogleAuthSubmitting(true);
        setGoogleAuthError('');
        setGoogleAuthorizationUrl('');
        setGoogleAuthSessionId(null);

        try {
            const oauthBaseUrl = apiBaseUrl.replace(/\/api\/platform$/, '/oauth');
            const createSessionData = await apiClient.post(`${oauthBaseUrl}/sessions/`, {
                handler: {
                    provider_and_purpose: 'google_group_enrollment',
                    course_id: Number(courseId),
                },
            });

            setGoogleAuthorizationUrl(createSessionData.authorization_url || '');
            setGoogleAuthSessionId(createSessionData.session_id || null);
        } catch (error) {
            setGoogleAuthError(error?.message || 'Failed to authorize with Google.');
        } finally {
            setGoogleAuthSubmitting(false);
        }
    }

    const openGoogleWorkspaceDialog = async () => {
        closeEnrollMenu();
        setGoogleAuthError('');
        setGoogleGroupsError('');
        setGoogleGroups([]);
        setSelectedGroups(['all']);
        setGoogleGroupsDialogOpen(false);
        setGoogleWorkspaceDialogOpen(true);
        await createGoogleOAuthSession();
    }

    const closeGoogleWorkspaceDialog = () => {
        if (googleAuthSubmitting) {
            return;
        }
        setGoogleWorkspaceDialogOpen(false);
    }

    const delay = (ms) => new Promise((resolve) => {
        window.setTimeout(resolve, ms);
    });

    const pollOAuthSessionUntilCompleted = async (sessionId) => {
        const maxAttempts = 60;

        for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
            const data = await apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/oauth-session/${sessionId}/`);

            if (data.state === 'COMPLETED') {
                return;
            }

            if (data.state === 'FAILED') {
                throw new Error(localeMessages['enrollment_failed'] || 'Authorization failed.');
            }

            await delay(2000);
        }

        throw new Error('Timed out waiting for Google authorization to complete.');
    }

    const fetchGroups = async (sessionId) => {
        const data = await apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/oauth-session/${sessionId}/get_groups`);

        const groups = Array.isArray(data?.groups) ? data.groups : [];
        return groups
            .filter((group) => group && group.id)
            .map((group) => ({
                id: String(group.id),
                name: group.name || String(group.id),
            }));
    }

    const enrollUsersByGroups = async (sessionId, groups) => {
        await apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/oauth-session/${sessionId}/enroll_users`, {
            groups,
        });
    }

    const authorizeWithGoogle = async () => {
        if (!googleAuthSessionId) {
            return;
        }

        setGoogleAuthSubmitting(true);
        setGoogleAuthError('');
        setGoogleGroupsError('');

        try {
            await pollOAuthSessionUntilCompleted(googleAuthSessionId);

            const groups = await fetchGroups(googleAuthSessionId);
            setGoogleGroups(groups);

            if (groups.length === 0) {
                setSelectedGroups(['all']);
                await enrollUsersByGroups(googleAuthSessionId, ['all']);
                setGoogleWorkspaceDialogOpen(false);
                successCallback(localeMessages['imported_from_google_success'] || 'Learners imported from Google Workspace successfully.');
                return;
            }

            setSelectedGroups(['all']);
            setGoogleWorkspaceDialogOpen(false);
            setGoogleGroupsDialogOpen(true);
        } catch (error) {
            setGoogleAuthError(error?.message || 'Failed to authorize with Google.');
        } finally {
            setGoogleAuthSubmitting(false);
        }
    }

    const closeGoogleGroupsDialog = () => {
        setGoogleGroupsDialogOpen(false);
        setGoogleGroupsError('');
    }

    const toggleAllGroups = (checked) => {
        if (checked) {
            setSelectedGroups(['all']);
            return;
        }
        setSelectedGroups([]);
    }

    const toggleSingleGroup = (groupId) => {
        setSelectedGroups((previousSelectedGroups) => {
            const withoutAll = previousSelectedGroups.filter((value) => value !== 'all');

            if (withoutAll.includes(groupId)) {
                return withoutAll.filter((value) => value !== groupId);
            }

            return [...withoutAll, groupId];
        });
    }

    const submitSelectedGoogleGroups = async () => {
        if (selectedGroups.length === 0) {
            setGoogleGroupsError(localeMessages['group_required'] || 'Please select at least one group.');
            return;
        }

        if (!googleAuthSessionId) {
            setGoogleGroupsError(localeMessages['enrollment_failed'] || 'Failed to enroll users.');
            return;
        }

        setGoogleAuthSubmitting(true);
        setGoogleGroupsError('');

        try {
            await enrollUsersByGroups(googleAuthSessionId, selectedGroups);
            setGoogleGroupsDialogOpen(false);
            successCallback(localeMessages['imported_from_google_success'] || 'Learners imported from Google Workspace successfully.');
        } catch (error) {
            setGoogleGroupsError(error?.message || 'Failed to enroll users.');
        } finally {
            setGoogleAuthSubmitting(false);
        }
    }

    const closeManualEnrollDialog = () => {
        if (manualEnrollSubmitting) {
            return;
        }
        setManualEnrollOpen(false);
        setManualEnrollError('');
    }

    const submitManualEnrollment = async () => {
        const email = manualEnrollEmail.trim();
        if (!email) {
            setManualEnrollError(localeMessages['email_required'] || 'Email is required.');
            return;
        }

        setManualEnrollSubmitting(true);
        setManualEnrollError('');

        try {
            await apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/enrollments/`, {
                learner_email: email,
            });
            successCallback(localeMessages['enrollment_success'] || 'Learner enrolled successfully.');
            setManualEnrollEmail('');
            setManualEnrollOpen(false);
        } catch (error) {
            console.error('Error enrolling learner:', error);
            setManualEnrollError(localeMessages['enrollment_failed'] || 'Failed to enroll learner.');
        } finally {
            setManualEnrollSubmitting(false);
        }
    }

    return (<>
            <Button
                variant="outlined"
                startIcon={<PersonAddAlt1Icon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />}
                endIcon={<ArrowDropDownIcon />}
                sx={(theme) => ({
                    marginBottom: 2,
                    minWidth: 190,
                    width: { xs: '100%', md: 'auto' },
                    justifyContent: 'flex-start',
                    '& .MuiButton-endIcon': {
                        marginInlineStart: 'auto',
                        marginInlineEnd: 0,
                    },
                    marginInlineEnd: { xs: 0, md: 1 },
                    ...(theme.palette.mode === 'dark' && {
                        borderColor: 'rgba(184, 190, 255, 0.5)',
                        '&:hover': { borderColor: 'rgba(210, 214, 255, 0.5)' },
                    }),
                })}
                onClick={openEnrollMenu}
                >
                {localeMessages['enroll_learner'] }
            </Button>
            <Menu
                anchorEl={enrollMenuAnchorEl}
                open={isEnrollMenuOpen}
                onClose={closeEnrollMenu}
                disableRestoreFocus
                slotProps={{
                    list: {
                        ref: enrollMenuListRef,
                        onKeyDown: handleEnrollMenuKeyDown,
                        autoFocus: true,
                        sx: {
                            minWidth: 200,
                            py: 0,
                        }
                    },
                    paper: {
                        sx: {
                            marginTop: "1px",
                            border: '1px solid',
                            borderColor: 'border.main',
                        }
                    }
                }}
                >
                <MenuItem onClick={openManualEnrollDialog} sx={{ fontSize: '0.87rem', px: 1 }}>
                    {localeMessages['manual_email']}
                </MenuItem>
                {userRole === 'admin' && availableFeatures.includes('google_workspace_enroll') && (
                    <MenuItem onClick={openGoogleWorkspaceDialog} sx={{ fontSize: '0.87rem', px: 1 }}>
                        {localeMessages['from_google_workspace']}
                    </MenuItem>
                )}
            </Menu>

            <Dialog
                open={manualEnrollOpen}
                onClose={closeManualEnrollDialog}
                fullWidth
                maxWidth="sm"
                TransitionProps={{
                    onEntered: () => {
                        manualEnrollInputRef.current?.focus();
                    }
                }}
            >
                <DialogTitle>{localeMessages['enroll_learner'] || 'Enroll Learner'}</DialogTitle>
                <DialogContent>
                    <TextField
                        fullWidth
                        autoFocus
                        inputRef={manualEnrollInputRef}
                        margin="dense"
                        type="email"
                        label={localeMessages['email'] || 'Email'}
                        value={manualEnrollEmail}
                        onChange={(event) => setManualEnrollEmail(event.target.value)}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter') {
                                event.preventDefault();
                                submitManualEnrollment();
                            }
                        }}
                        disabled={manualEnrollSubmitting}
                    />
                    {manualEnrollError && <Alert severity="error" sx={{ mt: 2 }}>{manualEnrollError}</Alert>}
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeManualEnrollDialog} disabled={manualEnrollSubmitting}>
                        {localeMessages['cancel'] || 'Cancel'}
                    </Button>
                    <Button variant="contained" onClick={submitManualEnrollment} disabled={manualEnrollSubmitting}>
                        {localeMessages['enroll'] || 'Enroll'}
                    </Button>
                </DialogActions>
            </Dialog>

            <Dialog
                open={googleWorkspaceDialogOpen}
                onClose={closeGoogleWorkspaceDialog}
                fullWidth
                maxWidth="sm"
            >
                <DialogTitle sx={{ px: 3, pt: 3, pb: 1.5 }}>{localeMessages['from_google_workspace']}</DialogTitle>
                <DialogContent sx={{ px: 3, py: 1.5 }}>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                        {localeMessages['google_workspace_description']}
                    </Typography>
                    <Typography variant="body2">
                        {localeMessages['authorize_description']}
                    </Typography>
                    {googleAuthError && <Alert severity="error" sx={{ mt: 2 }}>{googleAuthError}</Alert>}
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 3, pt: 1.5 }}>
                    <Button onClick={closeGoogleWorkspaceDialog} disabled={googleAuthSubmitting}>
                        {localeMessages['cancel'] || 'Cancel'}
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={<GoogleIcon />}
                        target="_blank"
                        rel="noopener noreferrer"
                        href={googleAuthorizationUrl || undefined}
                        onClick={authorizeWithGoogle}
                        disabled={googleAuthSubmitting || !googleAuthorizationUrl || !googleAuthSessionId}
                    >
                        {localeMessages['authorize_button']}
                    </Button>
                </DialogActions>
            </Dialog>

            <Dialog
                open={googleGroupsDialogOpen}
                onClose={closeGoogleGroupsDialog}
                fullWidth
                maxWidth="sm"
            >
                <DialogTitle sx={{ px: 3, pt: 3, pb: 1.5 }}>
                    {localeMessages['select_google_groups'] || 'Choose groups to enroll'}
                </DialogTitle>
                <DialogContent sx={{ px: 3, py: 1.5 }}>
                    <Typography variant="body2" sx={{ mb: 2 }}>
                        {localeMessages['google_group_question'] || 'Which group of people do you want to enroll in this course?'}
                    </Typography>
                    <FormGroup>
                        <FormControlLabel
                            control={(
                                <Checkbox
                                    checked={selectedGroups.includes('all')}
                                    onChange={(event) => toggleAllGroups(event.target.checked)}
                                />
                            )}
                            label={localeMessages['all'] || 'All'}
                        />
                        {googleGroups.map((group) => (
                            <FormControlLabel
                                key={group.id}
                                control={(
                                    <Checkbox
                                        checked={!selectedGroups.includes('all') && selectedGroups.includes(group.id)}
                                        onChange={() => toggleSingleGroup(group.id)}
                                    />
                                )}
                                label={group.name}
                            />
                        ))}
                    </FormGroup>
                    {googleGroupsError && <Alert severity="error" sx={{ mt: 2 }}>{googleGroupsError}</Alert>}
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 3, pt: 1.5 }}>
                    <Button onClick={closeGoogleGroupsDialog} disabled={googleAuthSubmitting}>
                        {localeMessages['cancel'] || 'Cancel'}
                    </Button>
                    <Button variant="contained" onClick={submitSelectedGoogleGroups} disabled={googleAuthSubmitting}>
                        {localeMessages['enroll'] || 'Enroll'}
                    </Button>
                </DialogActions>
            </Dialog>
        </>)
}

export default EnrollMenu;
