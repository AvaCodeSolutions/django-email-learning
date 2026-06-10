import { useState, useEffect } from 'react';
import {
    Alert,
    Box,
    Button,
    FormControlLabel,
    Grid,
    InputLabel,
    MenuItem,
    Select,
    Switch,
    Tooltip,
    Typography,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
} from '@mui/material';
import RequiredTextField from '../../../src/components/RequiredTextField';
import { useAppContext } from '../../../src/render';
import apiClient from '../../../src/apiClient.js';

const AssignmentForm = ({
    cancelCallback,
    successCallback,
    courseId,
    assignmentId,
    contentId,
    initialTitle,
    initialDescription,
    initialIsBlocking,
    initialDeadlineDays,
    initialRequiresTextSubmission,
    initialRequiresFileSubmission,
    initialReminderIntervalDays,
    initialWaitingPeriod,
    header,
}) => {
    const { localeMessages, apiBaseUrl } = useAppContext();
    const organizationId = localStorage.getItem('activeOrganizationId');

    const initialWaitingPeriodValue = initialWaitingPeriod ? initialWaitingPeriod.period : 1;
    const initialWaitingPeriodUnit = initialWaitingPeriod ? initialWaitingPeriod.type : 'days';
    const initialHasDeadline =
        initialDeadlineDays !== undefined ? Number(initialDeadlineDays) > 0 : true;
    const initialDeadlineDaysValue =
        initialDeadlineDays !== undefined ? Number(initialDeadlineDays) : 7;

    const [assignmentIdentifier, setAssignmentIdentifier] = useState(assignmentId);
    const [contentIdentifier, setContentIdentifier] = useState(contentId);

    const [title, setTitle] = useState(initialTitle || '');
    const [description, setDescription] = useState(initialDescription || '');
    const [isBlocking, setIsBlocking] = useState(initialIsBlocking ?? true);
    const [hasDeadline, setHasDeadline] = useState(initialHasDeadline);
    const [deadlineDays, setDeadlineDays] = useState(initialDeadlineDaysValue);
    const [requiresTextSubmission, setRequiresTextSubmission] = useState(
        initialRequiresTextSubmission ?? true
    );
    const [requiresFileSubmission, setRequiresFileSubmission] = useState(
        initialRequiresFileSubmission ?? false
    );
    const initialReminderIntervalValue = !initialHasDeadline
        ? Number(initialReminderIntervalDays || 0)
        : 0;
    const initialReminderEnabled = Number(initialReminderIntervalValue) > 0;
    const [hasReminderInterval, setHasReminderInterval] = useState(initialReminderEnabled);
    const [reminderIntervalDays, setReminderIntervalDays] = useState(initialReminderIntervalValue);
    const [waitingPeriod, setWaitingPeriod] = useState(initialWaitingPeriodValue);
    const [waitingPeriodUnit, setWaitingPeriodUnit] = useState(initialWaitingPeriodUnit);

    const [titleHelperText, setTitleHelperText] = useState('');
    const [descriptionHelperText, setDescriptionHelperText] = useState('');
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const [confirmCloseDialogOpen, setConfirmCloseDialogOpen] = useState(false);

    const savedSnapshot = {
        title: initialTitle || '',
        description: initialDescription || '',
        isBlocking: initialIsBlocking ?? true,
        hasDeadline: initialHasDeadline,
        deadlineDays: initialDeadlineDaysValue,
        hasReminderInterval: initialReminderEnabled,
        reminderIntervalDays: initialReminderIntervalValue,
        requiresTextSubmission: initialRequiresTextSubmission ?? true,
        requiresFileSubmission: initialRequiresFileSubmission ?? false,
        waitingPeriod: String(initialWaitingPeriodValue),
        waitingPeriodUnit: initialWaitingPeriodUnit,
    };

    const hasUnsavedChanges =
        title !== savedSnapshot.title ||
        description !== savedSnapshot.description ||
        isBlocking !== savedSnapshot.isBlocking ||
        hasDeadline !== savedSnapshot.hasDeadline ||
        deadlineDays !== savedSnapshot.deadlineDays ||
        hasReminderInterval !== savedSnapshot.hasReminderInterval ||
        Number(reminderIntervalDays) !== Number(savedSnapshot.reminderIntervalDays) ||
        requiresTextSubmission !== savedSnapshot.requiresTextSubmission ||
        requiresFileSubmission !== savedSnapshot.requiresFileSubmission ||
        String(waitingPeriod) !== savedSnapshot.waitingPeriod ||
        waitingPeriodUnit !== savedSnapshot.waitingPeriodUnit;

    useEffect(() => {
        if (!successMessage) return;
        const id = window.setTimeout(() => setSuccessMessage(''), 4000);
        return () => window.clearTimeout(id);
    }, [successMessage]);

    const validateForm = () => {
        let valid = true;
        if (!title) {
            setTitleHelperText(localeMessages['assignment_title_required']);
            valid = false;
        } else {
            setTitleHelperText('');
        }
        if (!description) {
            setDescriptionHelperText(localeMessages['assignment_description_required']);
            valid = false;
        } else {
            setDescriptionHelperText('');
        }
        if (!requiresFileSubmission && !requiresTextSubmission) {
            setErrorMessage(localeMessages['assignment_submission_required']);
            valid = false;
        }
        if (
            !hasDeadline &&
            hasReminderInterval &&
            (Number(reminderIntervalDays) <= 0 || reminderIntervalDays === '')
        ) {
            setErrorMessage(
                localeMessages['reminder_interval_days_required'] ||
                    'Reminder interval days must be greater than 0 when reminders are enabled.'
            );
            valid = false;
        }
        if (valid) {
            setErrorMessage('');
        }
        return valid;
    };

    const buildPayload = (forCreate) => {
        const finalDeadlineDays = hasDeadline ? deadlineDays : 0;
        const normalizedReminderIntervalDays = !hasDeadline && hasReminderInterval
            ? Number(reminderIntervalDays)
            : 0;
        const assignmentPayload = {
            title,
            description,
            is_blocking: isBlocking,
            deadline_days: finalDeadlineDays,
            requires_text_submission: requiresTextSubmission,
            requires_file_submission: requiresFileSubmission,
            reminder_interval_days: normalizedReminderIntervalDays,
            ...(forCreate ? { type: 'assignment' } : {}),
        };

        if (forCreate) {
            return {
                content: assignmentPayload,
                waiting_period: { period: waitingPeriod, type: waitingPeriodUnit },
            };
        }
        return {
            assignment: assignmentPayload,
            waiting_period: { period: waitingPeriod, type: waitingPeriodUnit },
        };
    };

    const createAssignment = () => {
        if (!validateForm()) {
            if (!errorMessage) {
                setErrorMessage(localeMessages['fix_errors']);
            }
            return;
        }
        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/`, buildPayload(true))
            .then((data) => {
                setErrorMessage('');
                setAssignmentIdentifier(data.assignment.id);
                setContentIdentifier(data.id);
                setSuccessMessage(localeMessages['assignment_saved_success']);
                successCallback?.();
            })
            .catch(() => {
                setSuccessMessage('');
                setErrorMessage(localeMessages['save_failed']);
            });
    };

    const updateAssignment = () => {
        if (!validateForm()) {
            if (!errorMessage) {
                setErrorMessage(localeMessages['fix_errors']);
            }
            return;
        }
        apiClient.post(
            `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentIdentifier}/`,
            buildPayload(false)
        )
            .then(() => {
                setErrorMessage('');
                setSuccessMessage(localeMessages['assignment_saved_success']);
                successCallback?.();
            })
            .catch(() => {
                setSuccessMessage('');
                setErrorMessage(localeMessages['save_failed']);
            });
    };

    const handleSave = () => {
        if (assignmentIdentifier) {
            updateAssignment();
        } else {
            createAssignment();
        }
    };

    const handleCancel = () => {
        if (hasUnsavedChanges) {
            setConfirmCloseDialogOpen(true);
        } else {
            cancelCallback?.();
        }
    };

    useEffect(() => {
        if (hasDeadline) {
            if (hasReminderInterval) {
                setHasReminderInterval(false);
            }
            if (reminderIntervalDays !== 0) {
                setReminderIntervalDays(0);
            }
        }
    }, [hasDeadline, hasReminderInterval, reminderIntervalDays]);

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Typography variant="h2" sx={{ fontSize: '1.5rem' }}>
                    {header || localeMessages['new_assignment']}
                </Typography>
            </Box>

            {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
            {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

            <RequiredTextField
                label={localeMessages['assignment_title']}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                helperText={titleHelperText}
                error={!!titleHelperText}
                sx={{ mb: 2, width: '100%' }}
            />

            <RequiredTextField
                label={localeMessages['assignment_description']}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                helperText={descriptionHelperText}
                error={!!descriptionHelperText}
                multiline
                minRows={5}
                sx={{ mb: 3, width: '100%' }}
            />

            {/* Settings section — mirrors QuizForm grid layout */}
            <Box sx={{ mt: 1 }}>
                <Typography variant="h6" sx={{ mb: 2, fontSize: '1.1rem', color: 'secondary.main' }}>
                    {localeMessages['quiz_settings']}
                </Typography>

                <Grid container spacing={3}>

                    {/* Blocking */}
                    <Grid size={{ xs: 12 }}>
                        <Box>
                            <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                {localeMessages['blocking_assignment']}
                            </InputLabel>
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={isBlocking}
                                        onChange={(e) => setIsBlocking(e.target.checked)}
                                    />
                                }
                                label={localeMessages['blocking_assignment']}
                            />
                            <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.5 }}>
                                {localeMessages['blocking_assignment_tooltip']}
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Waiting period */}
                    <Grid size={{ xs: 12 }}>
                        <Tooltip title={localeMessages['assignment_waiting_tooltip']} placement="top-start">
                            <Box>
                                <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                    {localeMessages['waiting_period']}
                                </InputLabel>
                                <Box sx={{ display: 'flex', gap: 1 }}>
                                    <RequiredTextField
                                        label={localeMessages['period']}
                                        type="number"
                                        value={waitingPeriod}
                                        onChange={(e) => setWaitingPeriod(e.target.value)}
                                        slotProps={{ htmlInput: { min: 1 } }}
                                    />
                                    <Select
                                        size="small"
                                        value={waitingPeriodUnit}
                                        onChange={(e) => setWaitingPeriodUnit(e.target.value)}
                                        sx={{ minWidth: '100px' }}
                                    >
                                        <MenuItem value="days">{localeMessages['days']}</MenuItem>
                                        <MenuItem value="hours">{localeMessages['hours']}</MenuItem>
                                    </Select>
                                </Box>
                            </Box>
                        </Tooltip>
                    </Grid>

                    {/* Deadline */}
                    <Grid size={{ xs: 12, md: 6 }}>
                        <Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                <InputLabel sx={{ fontSize: '0.9rem', color: 'text.secondary', m: 0 }}>
                                    {localeMessages['assignment_deadline']}
                                </InputLabel>
                                <FormControlLabel
                                    control={
                                        <Switch
                                            checked={hasDeadline}
                                            onChange={(e) => {
                                                setHasDeadline(e.target.checked);
                                                if (!e.target.checked) {
                                                    setDeadlineDays(0);
                                                } else if (!deadlineDays || deadlineDays === 0) {
                                                    setDeadlineDays(7);
                                                }
                                            }}
                                            size="small"
                                        />
                                    }
                                    label=""
                                    sx={{ m: 0 }}
                                />
                            </Box>
                            <Tooltip title={localeMessages['deadline_tooltip']} placement="top-start">
                                <RequiredTextField
                                    label={localeMessages['days']}
                                    type="number"
                                    value={deadlineDays}
                                    onChange={(e) => { if (hasDeadline) setDeadlineDays(e.target.value); }}
                                    sx={{ width: '100%' }}
                                    slotProps={{ htmlInput: { min: hasDeadline ? 1 : 0 } }}
                                    disabled={!hasDeadline}
                                />
                            </Tooltip>
                        </Box>
                    </Grid>

                    {/* Requires text submission */}
                    {!hasDeadline && (
                        <Grid size={{ xs: 12, md: 6 }}>
                            <Tooltip
                                title={localeMessages['reminder_interval_days_tooltip']}
                                placement="top-start"
                            >
                                <Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                        <InputLabel sx={{ fontSize: '0.9rem', color: 'text.secondary', m: 0 }}>
                                            {localeMessages['reminder_interval_days']}
                                        </InputLabel>
                                        <FormControlLabel
                                            control={
                                                <Switch
                                                    checked={hasReminderInterval}
                                                    onChange={(e) => {
                                                        setHasReminderInterval(e.target.checked);
                                                        if (!e.target.checked) {
                                                            setReminderIntervalDays(0);
                                                        } else if (
                                                            reminderIntervalDays === 0 ||
                                                            reminderIntervalDays === '0' ||
                                                            reminderIntervalDays === ''
                                                        ) {
                                                            setReminderIntervalDays(1);
                                                        }
                                                    }}
                                                    size="small"
                                                />
                                            }
                                            label=""
                                            sx={{ m: 0 }}
                                        />
                                    </Box>
                                    <RequiredTextField
                                        label={localeMessages['days']}
                                        type="number"
                                        value={reminderIntervalDays}
                                        onChange={(e) => {
                                            if (hasReminderInterval) {
                                                setReminderIntervalDays(e.target.value);
                                            }
                                        }}
                                        sx={{ width: '100%' }}
                                        slotProps={{ htmlInput: { min: hasReminderInterval ? 1 : 0 } }}
                                        disabled={!hasReminderInterval}
                                    />
                                </Box>
                            </Tooltip>
                        </Grid>
                    )}

                    <Grid size={{ xs: 12 }}>
                        <Box>
                            <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                {localeMessages['requires_text_submission']}
                            </InputLabel>
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={requiresTextSubmission}
                                        onChange={(e) => setRequiresTextSubmission(e.target.checked)}
                                    />
                                }
                                label={localeMessages['requires_text_submission']}
                            />
                        </Box>
                    </Grid>

                    {/* Requires file submission */}
                    <Grid size={{ xs: 12 }}>
                        <Box>
                            <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                {localeMessages['requires_file_submission']}
                            </InputLabel>
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={requiresFileSubmission}
                                        onChange={(e) => setRequiresFileSubmission(e.target.checked)}
                                    />
                                }
                                label={localeMessages['requires_file_submission']}
                            />
                        </Box>
                    </Grid>

                </Grid>
            </Box>

            {/* Sticky action bar */}
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', position: 'sticky', bottom: 0, backgroundColor: 'background.paper', py: 2, zIndex: 99 }}>
                <Button variant="outlined" onClick={handleCancel} sx={{ mr: 1 }}>
                    {localeMessages['cancel']}
                </Button>
                <Button variant="contained" color="secondary" onClick={handleSave}>
                    {localeMessages['save_assignment']}
                </Button>
            </Box>

            {/* Unsaved-changes confirm dialog */}
            <Dialog open={confirmCloseDialogOpen} onClose={() => setConfirmCloseDialogOpen(false)}>
                <DialogTitle>{localeMessages['cancel']}</DialogTitle>
                <DialogContent>
                    <DialogContentText>{localeMessages['unsaved_changes_warning']}</DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setConfirmCloseDialogOpen(false)}>
                        {localeMessages['back']}
                    </Button>
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

export default AssignmentForm;
