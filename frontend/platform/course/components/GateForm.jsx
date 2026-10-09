import { useState } from 'react';
import {
    Alert,
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    FormControlLabel,
    Grid,
    InputLabel,
    MenuItem,
    Select,
    Switch,
    TextField,
    Tooltip,
    Typography,
} from '@mui/material';
import RequiredTextField from '../../../src/components/RequiredTextField';
import ContentEditor from '../../../src/components/ContentEditor.jsx';
import { useAppContext } from '../../../src/render';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';
import TrackSelect from './TrackSelect.jsx';
import { errorMessageFrom, fromTrackValue, toTrackValue } from './branching.js';

const KEY_PATTERN = /^[-a-zA-Z0-9_]+$/;

// RequiredTextField colours its helper text as an error; these fields also use it for a hint.
const helperTextColor = (hasError) => ({ formHelperText: { sx: { color: hasError ? 'errorText.main' : 'text.secondary' } } });

// The editor leaves markup such as <p></p> behind once its text is deleted.
const isBlankHtml = (html) => !html || (!/<img/i.test(html) && !html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim());

// A key suggested from the title while the author has not typed one of their own.
const keyFromTitle = (title) => title
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 100);

/**
 * Authoring for a gate: a step that holds learners until it is unlocked from outside the
 * course, with an optional message emailed as they reach it and an optional timeout.
 */
const GateForm = ({
    cancelCallback,
    successCallback,
    courseId,
    contentId,
    initialTitle,
    initialKey,
    initialMessage,
    initialTimeoutDays,
    initialTimeoutAction,
    initialWaitingPeriod,
    header,
    tracks = [],
    initialTrackId = null,
}) => {
    const { localeMessages, userRole, direction, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');
    const canEdit = userRole !== 'viewer';

    const [form, setForm] = useState(() => {
        const hasTimeout = Number(initialTimeoutDays || 0) > 0;
        return {
            title: initialTitle || '',
            key: initialKey || '',
            message: initialMessage || '',
            hasTimeout,
            timeoutDays: hasTimeout ? Number(initialTimeoutDays) : 14,
            timeoutAction: initialTimeoutAction || 'deactivate',
            waitingPeriod: initialWaitingPeriod ? initialWaitingPeriod.period : 1,
            waitingPeriodUnit: initialWaitingPeriod ? initialWaitingPeriod.type : 'hours',
            trackId: toTrackValue(initialTrackId),
        };
    });
    const [savedSignature, setSavedSignature] = useState(() => JSON.stringify(form));
    const [savedTrackId, setSavedTrackId] = useState(toTrackValue(initialTrackId));
    const [contentIdentifier, setContentIdentifier] = useState(contentId);
    // A new gate's key follows its title until the author edits the key themselves.
    const [keyTouched, setKeyTouched] = useState(Boolean(initialKey));

    const [titleHelperText, setTitleHelperText] = useState('');
    const [keyHelperText, setKeyHelperText] = useState('');
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [confirmCloseDialogOpen, setConfirmCloseDialogOpen] = useState(false);

    const update = (changes) => {
        setSuccessMessage('');
        setForm((current) => ({ ...current, ...changes }));
    };

    const updateTitle = (title) => {
        update(keyTouched ? { title } : { title, key: keyFromTitle(title) });
    };

    const validate = () => {
        const titleError = form.title.trim() ? '' : (localeMessages['gate_title_required'] || 'A gate needs a title.');
        let keyError = '';
        if (!form.key.trim()) {
            keyError = localeMessages['gate_key_required'] || 'A gate needs a key.';
        } else if (!KEY_PATTERN.test(form.key.trim())) {
            keyError = localeMessages['gate_key_invalid'] || 'Use only letters, numbers, hyphens and underscores.';
        }
        setTitleHelperText(titleError);
        setKeyHelperText(keyError);
        const valid = !titleError && !keyError;
        setErrorMessage(valid ? '' : (localeMessages['fix_errors'] || ''));
        return valid;
    };

    const gatePayload = () => ({
        title: form.title.trim(),
        key: form.key.trim(),
        message: isBlankHtml(form.message) ? '' : form.message,
        timeout_days: form.hasTimeout ? Number(form.timeoutDays) : 0,
        timeout_action: form.timeoutAction,
    });

    const save = () => {
        if (!validate()) {
            return;
        }
        const waitingPeriod = { period: form.waitingPeriod, type: form.waitingPeriodUnit };
        const request = contentIdentifier
            ? apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentIdentifier}/`, {
                gate: gatePayload(),
                waiting_period: waitingPeriod,
                ...(form.trackId !== savedTrackId ? { track_id: fromTrackValue(form.trackId) } : {}),
            })
            : apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/`, {
                content: { ...gatePayload(), type: 'gate' },
                waiting_period: waitingPeriod,
                ...(form.trackId !== '' ? { track_id: fromTrackValue(form.trackId) } : {}),
            });
        request
            .then((data) => {
                setSavedSignature(JSON.stringify(form));
                setSavedTrackId(form.trackId);
                setKeyTouched(true);
                setContentIdentifier(data?.id ?? contentIdentifier);
                setErrorMessage('');
                setSuccessMessage(localeMessages['gate_saved_success'] || 'Gate saved.');
                successCallback?.();
            })
            .catch((error) => {
                setSuccessMessage('');
                setErrorMessage(errorMessageFrom(error, localeMessages['gate_save_failed'] || 'Could not save the gate.'));
            });
    };

    const hasUnsavedChanges = JSON.stringify(form) !== savedSignature || form.trackId !== savedTrackId;
    const handleCancel = () => {
        if (hasUnsavedChanges) {
            setConfirmCloseDialogOpen(true);
        } else {
            cancelCallback?.();
        }
    };

    const settingLabel = { mb: 1, fontSize: '0.9rem', color: 'text.secondary' };
    const stickyBar = { display: 'flex', justifyContent: 'flex-end', position: 'sticky', bottom: 0, backgroundColor: 'background.paper', py: 2, zIndex: 99 };

    return (
        <Box sx={{ px: { xs: '14px', sm: 3 }, py: 3 }}>
            <Typography variant="h2" sx={{ fontSize: '1.5rem', mb: 1 }}>
                {header || localeMessages['new_gate'] || 'New Gate'}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {localeMessages['gate_intro']}
            </Typography>

            {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
            {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

            <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid size={{ xs: 12, md: 7 }}>
                    <RequiredTextField
                        label={localeMessages['title'] || 'Title'}
                        value={form.title}
                        onChange={(event) => updateTitle(event.target.value)}
                        helperText={titleHelperText || localeMessages['gate_title_help']}
                        error={!!titleHelperText}
                        disabled={!canEdit}
                        slotProps={{ htmlInput: { maxLength: 500 }, ...helperTextColor(!!titleHelperText) }}
                        sx={{ width: '100%' }}
                    />
                </Grid>
                <Grid size={{ xs: 12, md: 5 }}>
                    <RequiredTextField
                        label={localeMessages['gate_key'] || 'Key'}
                        value={form.key}
                        onChange={(event) => {
                            setKeyTouched(true);
                            update({ key: event.target.value });
                        }}
                        helperText={keyHelperText || localeMessages['gate_key_help']}
                        error={!!keyHelperText}
                        disabled={!canEdit}
                        slotProps={{ htmlInput: { maxLength: 100, style: { fontFamily: 'monospace' } }, ...helperTextColor(!!keyHelperText) }}
                        sx={{ width: '100%' }}
                    />
                </Grid>
            </Grid>

            <InputLabel sx={settingLabel}>{localeMessages['gate_message'] || 'Message to learners'}</InputLabel>
            <ContentEditor
                initialContent={form.message}
                contentUpdateCallback={(message) => update({ message })}
                disabled={!canEdit}
                defaultDirection={direction}
            />
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, mb: 3 }}>
                {localeMessages['gate_message_help']}
            </Typography>

            <Typography variant="h6" sx={{ mb: 2, fontSize: '1.1rem', color: 'secondary.main' }}>
                {localeMessages['gate_settings'] || 'Gate Settings'}
            </Typography>
            <Grid container spacing={3}>
                <Grid size={{ xs: 12 }}>
                    <InputLabel sx={settingLabel}>{localeMessages['waiting_period']}</InputLabel>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        <RequiredTextField
                            label={localeMessages['period']}
                            type="number"
                            value={form.waitingPeriod}
                            onChange={(event) => update({ waitingPeriod: event.target.value })}
                            disabled={!canEdit}
                            slotProps={{ htmlInput: { min: 1 } }}
                        />
                        <Select
                            size="small"
                            value={form.waitingPeriodUnit}
                            onChange={(event) => update({ waitingPeriodUnit: event.target.value })}
                            disabled={!canEdit}
                            sx={{ minWidth: '100px' }}
                        >
                            <MenuItem value="days">{localeMessages['days']}</MenuItem>
                            <MenuItem value="hours">{localeMessages['hours']}</MenuItem>
                        </Select>
                    </Box>
                </Grid>

                {tracks.length > 0 && (
                    <Grid size={{ xs: 12, md: 6 }}>
                        <TrackSelect tracks={tracks} value={form.trackId} onChange={(trackId) => update({ trackId })} fullWidth />
                    </Grid>
                )}

                <Grid size={{ xs: 12, md: 6 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <InputLabel sx={{ ...settingLabel, m: 0 }}>{localeMessages['gate_timeout'] || 'Timeout'}</InputLabel>
                        <FormControlLabel
                            control={
                                <Switch
                                    size="small"
                                    checked={form.hasTimeout}
                                    disabled={!canEdit}
                                    onChange={(event) => update({ hasTimeout: event.target.checked })}
                                    slotProps={{ input: { 'aria-label': localeMessages['gate_timeout'] || 'Timeout' } }}
                                />
                            }
                            label=""
                            sx={{ m: 0 }}
                        />
                    </Box>
                    <Tooltip title={localeMessages['gate_timeout_tooltip']} placement="top-start">
                        <RequiredTextField
                            label={localeMessages['days']}
                            type="number"
                            value={form.hasTimeout ? form.timeoutDays : 0}
                            onChange={(event) => update({ timeoutDays: event.target.value })}
                            disabled={!canEdit || !form.hasTimeout}
                            slotProps={{ htmlInput: { min: 1 } }}
                            sx={{ width: '100%' }}
                        />
                    </Tooltip>
                </Grid>

                {form.hasTimeout && (
                    <Grid size={{ xs: 12, md: 6 }}>
                        <InputLabel id="gate-timeout-action-label" sx={settingLabel}>{localeMessages['gate_timeout_action'] || 'When it times out'}</InputLabel>
                        <TextField
                            select
                            slotProps={{ select: { labelId: 'gate-timeout-action-label' } }}
                            size="small"
                            value={form.timeoutAction}
                            onChange={(event) => update({ timeoutAction: event.target.value })}
                            disabled={!canEdit}
                            sx={{ width: '100%' }}
                        >
                            <MenuItem value="deactivate">{localeMessages['gate_timeout_deactivate'] || 'Deactivate the enrollment'}</MenuItem>
                            <MenuItem value="continue">{localeMessages['gate_timeout_continue'] || 'Continue past the gate'}</MenuItem>
                        </TextField>
                    </Grid>
                )}
            </Grid>

            <Box sx={stickyBar}>
                <Button variant="outlined" onClick={handleCancel} sx={{ mr: 1 }}>
                    {localeMessages['cancel']}
                </Button>
                {canEdit && (
                    <Button variant="contained" color="secondary" onClick={save}>
                        {localeMessages['save_gate'] || 'Save Gate'}
                    </Button>
                )}
            </Box>

            <Dialog open={confirmCloseDialogOpen} onClose={() => setConfirmCloseDialogOpen(false)}>
                <DialogTitle>{localeMessages['cancel']}</DialogTitle>
                <DialogContent>
                    <DialogContentText>{localeMessages['unsaved_changes_warning']}</DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setConfirmCloseDialogOpen(false)}>{localeMessages['back']}</Button>
                    <Button
                        color="error"
                        onClick={() => {
                            setConfirmCloseDialogOpen(false);
                            cancelCallback?.();
                        }}
                    >
                        {localeMessages['close_without_saving']}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default GateForm;
