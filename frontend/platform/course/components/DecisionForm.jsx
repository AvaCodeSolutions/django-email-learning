import { lazy, Suspense, useState } from 'react';
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
    IconButton,
    InputLabel,
    LinearProgress,
    MenuItem,
    Select,
    Switch,
    Tab,
    Tabs,
    Tooltip,
    Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import DeleteIcon from '@mui/icons-material/Delete';
import RequiredTextField from '../../../src/components/RequiredTextField';
import { useAppContext } from '../../../src/render';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';
import TrackSelect from './TrackSelect.jsx';
import { errorMessageFrom, fromTrackValue, toTrackValue } from './branching.js';

const QuizBranching = lazy(() => import('./QuizBranching.jsx'));

// Answers are keyed on the client, so a new or reordered answer keeps its input while it has no id.
let nextOptionKey = 0;
const withKeys = (options) => options.map((option) => {
    nextOptionKey += 1;
    return { id: option.id ?? null, text: option.text, key: `option-${nextOptionKey}` };
});

// What the unsaved-changes check compares: the answers by id and text, not their client keys.
const signatureOf = (form) => JSON.stringify({ ...form, options: form.options.map((option) => [option.id, option.text]) });

/**
 * Authoring for a decision point: one question, the answers a learner picks from, and - once
 * saved - the rules that route each answer onto a track.
 */
const DecisionForm = ({
    cancelCallback,
    successCallback,
    onBranchingChange,
    courseId,
    contentId,
    initialTitle,
    initialPrompt,
    initialOptions,
    initialDeadlineDays,
    initialReminderIntervalDays,
    initialWaitingPeriod,
    header,
    tracks = [],
    initialTrackId = null,
}) => {
    const { localeMessages, userRole, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');
    const canEdit = userRole !== 'viewer';

    const [form, setForm] = useState(() => {
        const hasDeadline = Number(initialDeadlineDays || 0) > 0;
        const reminderDays = hasDeadline ? 0 : Number(initialReminderIntervalDays || 0);
        return {
            title: initialTitle || '',
            prompt: initialPrompt || '',
            options: withKeys(initialOptions?.length ? initialOptions : [{ text: '' }, { text: '' }]),
            hasDeadline,
            deadlineDays: hasDeadline ? Number(initialDeadlineDays) : 7,
            hasReminder: reminderDays > 0,
            reminderDays: reminderDays > 0 ? reminderDays : 1,
            waitingPeriod: initialWaitingPeriod ? initialWaitingPeriod.period : 1,
            waitingPeriodUnit: initialWaitingPeriod ? initialWaitingPeriod.type : 'days',
            trackId: toTrackValue(initialTrackId),
        };
    });
    const [savedSignature, setSavedSignature] = useState(() => signatureOf(form));
    const [savedTrackId, setSavedTrackId] = useState(toTrackValue(initialTrackId));
    const [savedOptions, setSavedOptions] = useState((initialOptions || []).filter((option) => option.id));
    const [contentIdentifier, setContentIdentifier] = useState(contentId);

    const [activeTab, setActiveTab] = useState('question');
    const [branchingVisited, setBranchingVisited] = useState(false);
    // Saving can remove answers, and their rules with them, so the rules reload after a save.
    const [branchingVersion, setBranchingVersion] = useState(0);

    const [titleHelperText, setTitleHelperText] = useState('');
    const [promptHelperText, setPromptHelperText] = useState('');
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [confirmCloseDialogOpen, setConfirmCloseDialogOpen] = useState(false);

    const update = (changes) => {
        setSuccessMessage('');
        setForm((current) => ({ ...current, ...changes }));
    };
    const updateOptions = (change) => {
        setSuccessMessage('');
        setForm((current) => ({ ...current, options: change(current.options) }));
    };

    const addOption = () => updateOptions((options) => [...options, ...withKeys([{ text: '' }])]);
    const removeOption = (index) => updateOptions((options) => options.filter((_, position) => position !== index));
    const editOption = (index, text) => updateOptions((options) => options.map((option, position) => (
        position === index ? { ...option, text } : option
    )));
    const moveOption = (index, offset) => updateOptions((options) => {
        const target = index + offset;
        if (target < 0 || target >= options.length) {
            return options;
        }
        const next = [...options];
        [next[index], next[target]] = [next[target], next[index]];
        return next;
    });

    const validate = () => {
        let valid = true;
        setTitleHelperText(form.title.trim() ? '' : (localeMessages['decision_title_required'] || 'A decision needs a title.'));
        setPromptHelperText(form.prompt.trim() ? '' : (localeMessages['decision_prompt_required'] || 'A decision needs a question.'));
        if (!form.title.trim() || !form.prompt.trim()) {
            valid = false;
        }
        let message = '';
        if (form.options.length < 2 || form.options.some((option) => !option.text.trim())) {
            message = localeMessages['decision_options_required'] || 'A decision needs at least two answers, and none of them can be empty.';
        } else if (!form.hasDeadline && form.hasReminder && !(Number(form.reminderDays) > 0)) {
            message = localeMessages['reminder_interval_days_required']
                || 'Reminder interval days must be greater than 0 when reminders are enabled.';
        }
        if (message) {
            valid = false;
        } else if (!valid) {
            message = localeMessages['fix_errors'] || '';
        }
        setErrorMessage(message);
        return valid;
    };

    const decisionPayload = () => ({
        title: form.title.trim(),
        prompt: form.prompt.trim(),
        deadline_days: form.hasDeadline ? Number(form.deadlineDays) : 0,
        reminder_interval_days: !form.hasDeadline && form.hasReminder ? Number(form.reminderDays) : 0,
        options: form.options.map((option) => (
            option.id ? { id: option.id, text: option.text.trim() } : { text: option.text.trim() }
        )),
    });

    const save = () => {
        if (!validate()) {
            return;
        }
        const waitingPeriod = { period: form.waitingPeriod, type: form.waitingPeriodUnit };
        const request = contentIdentifier
            ? apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentIdentifier}/`, {
                decision: decisionPayload(),
                waiting_period: waitingPeriod,
                ...(form.trackId !== savedTrackId ? { track_id: fromTrackValue(form.trackId) } : {}),
            })
            : apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/`, {
                content: { ...decisionPayload(), type: 'decision' },
                waiting_period: waitingPeriod,
                ...(form.trackId !== '' ? { track_id: fromTrackValue(form.trackId) } : {}),
            });
        request
            .then((data) => {
                // New answers only get their ids from the server, and rules can only point at saved answers.
                const decision = data?.decision;
                const nextForm = decision ? { ...form, options: withKeys(decision.options) } : form;
                if (decision) {
                    setSavedOptions(decision.options);
                }
                setForm(nextForm);
                setSavedSignature(signatureOf(nextForm));
                setSavedTrackId(form.trackId);
                setContentIdentifier(data?.id ?? contentIdentifier);
                setBranchingVersion((version) => version + 1);
                setErrorMessage('');
                setSuccessMessage(localeMessages['decision_saved_success'] || '');
                successCallback?.();
            })
            .catch((error) => {
                setSuccessMessage('');
                setErrorMessage(errorMessageFrom(error, localeMessages['decision_save_failed'] || 'Could not save the decision.'));
            });
    };

    const hasUnsavedChanges = signatureOf(form) !== savedSignature || form.trackId !== savedTrackId;
    const handleCancel = () => {
        if (hasUnsavedChanges) {
            setConfirmCloseDialogOpen(true);
        } else {
            cancelCallback?.();
        }
    };

    const optionLabel = (index) => (localeMessages['decision_option_label'] || 'Answer %(number)s').replace('%(number)s', String(index + 1));
    const settingLabel = { mb: 1, fontSize: '0.9rem', color: 'text.secondary' };
    const stickyBar = { display: 'flex', justifyContent: 'flex-end', position: 'sticky', bottom: 0, backgroundColor: 'background.paper', py: 2, zIndex: 99 };

    return (
        <Box sx={{ px: { xs: '14px', sm: 3 }, py: 3 }}>
            <Typography variant="h2" sx={{ fontSize: '1.5rem', mb: 2 }}>
                {header || localeMessages['new_decision'] || 'New Decision'}
            </Typography>

            {contentIdentifier && (
                <Tabs
                    value={activeTab}
                    onChange={(_, value) => {
                        setActiveTab(value);
                        if (value === 'branching') {
                            setBranchingVisited(true);
                        }
                    }}
                    sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
                >
                    <Tab value="question" label={localeMessages['decision_tab_question'] || 'Question'} />
                    <Tab value="branching" label={localeMessages['quiz_tab_branching'] || 'Branching'} />
                </Tabs>
            )}

            <Box role="tabpanel" sx={{ display: activeTab === 'question' ? 'block' : 'none' }}>
                {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
                {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

                <RequiredTextField
                    label={localeMessages['title'] || 'Title'}
                    value={form.title}
                    onChange={(event) => update({ title: event.target.value })}
                    helperText={titleHelperText}
                    error={!!titleHelperText}
                    disabled={!canEdit}
                    sx={{ mb: 2, width: '100%' }}
                />
                <RequiredTextField
                    label={localeMessages['decision_prompt'] || 'Question'}
                    value={form.prompt}
                    onChange={(event) => update({ prompt: event.target.value })}
                    helperText={promptHelperText || localeMessages['decision_prompt_help']}
                    error={!!promptHelperText}
                    disabled={!canEdit}
                    multiline
                    minRows={3}
                    sx={{ mb: 3, width: '100%' }}
                />

                <Typography variant="h6" sx={{ mb: 2, fontSize: '1.1rem', color: 'secondary.main' }}>
                    {localeMessages['decision_options'] || 'Answers'}
                </Typography>
                {form.options.map((option, index) => (
                    <Box key={option.key} data-testid="decision-option" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                        <RequiredTextField
                            label={optionLabel(index)}
                            value={option.text}
                            onChange={(event) => editOption(index, event.target.value)}
                            disabled={!canEdit}
                            slotProps={{ htmlInput: { maxLength: 500 } }}
                            sx={{ flex: 1 }}
                        />
                        {canEdit && (
                            <Box sx={{ display: 'flex' }}>
                                <Tooltip title={localeMessages['decision_move_option_up'] || 'Move answer up'}>
                                    <span>
                                        <IconButton size="small" aria-label={localeMessages['decision_move_option_up'] || 'Move answer up'} disabled={index === 0} onClick={() => moveOption(index, -1)}>
                                            <ArrowUpwardIcon fontSize="small" />
                                        </IconButton>
                                    </span>
                                </Tooltip>
                                <Tooltip title={localeMessages['decision_move_option_down'] || 'Move answer down'}>
                                    <span>
                                        <IconButton size="small" aria-label={localeMessages['decision_move_option_down'] || 'Move answer down'} disabled={index === form.options.length - 1} onClick={() => moveOption(index, 1)}>
                                            <ArrowDownwardIcon fontSize="small" />
                                        </IconButton>
                                    </span>
                                </Tooltip>
                                <Tooltip title={localeMessages['decision_remove_option'] || 'Remove answer'}>
                                    <span>
                                        <IconButton size="small" aria-label={localeMessages['decision_remove_option'] || 'Remove answer'} disabled={form.options.length <= 2} onClick={() => removeOption(index)}>
                                            <DeleteIcon fontSize="small" />
                                        </IconButton>
                                    </span>
                                </Tooltip>
                            </Box>
                        )}
                    </Box>
                ))}
                {canEdit && (
                    <Button variant="outlined" startIcon={<AddIcon />} onClick={addOption} sx={{ mb: 3 }}>
                        {localeMessages['decision_add_option'] || 'Add answer'}
                    </Button>
                )}

                <Typography variant="h6" sx={{ mb: 2, fontSize: '1.1rem', color: 'secondary.main' }}>
                    {localeMessages['decision_settings'] || 'Decision Settings'}
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
                            <InputLabel sx={{ ...settingLabel, m: 0 }}>{localeMessages['deadline_days'] || 'Deadline'}</InputLabel>
                            <FormControlLabel
                                control={
                                    <Switch
                                        size="small"
                                        checked={form.hasDeadline}
                                        disabled={!canEdit}
                                        onChange={(event) => update({ hasDeadline: event.target.checked, hasReminder: false })}
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
                                value={form.hasDeadline ? form.deadlineDays : 0}
                                onChange={(event) => update({ deadlineDays: event.target.value })}
                                disabled={!canEdit || !form.hasDeadline}
                                slotProps={{ htmlInput: { min: 1 } }}
                                sx={{ width: '100%' }}
                            />
                        </Tooltip>
                    </Grid>

                    {!form.hasDeadline && (
                        <Grid size={{ xs: 12, md: 6 }}>
                            <Tooltip title={localeMessages['reminder_interval_days_tooltip']} placement="top-start">
                                <Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                        <InputLabel sx={{ ...settingLabel, m: 0 }}>{localeMessages['reminder_interval_days']}</InputLabel>
                                        <FormControlLabel
                                            control={
                                                <Switch
                                                    size="small"
                                                    checked={form.hasReminder}
                                                    disabled={!canEdit}
                                                    onChange={(event) => update({ hasReminder: event.target.checked })}
                                                />
                                            }
                                            label=""
                                            sx={{ m: 0 }}
                                        />
                                    </Box>
                                    <RequiredTextField
                                        label={localeMessages['days']}
                                        type="number"
                                        value={form.hasReminder ? form.reminderDays : 0}
                                        onChange={(event) => update({ reminderDays: event.target.value })}
                                        disabled={!canEdit || !form.hasReminder}
                                        slotProps={{ htmlInput: { min: 1 } }}
                                        sx={{ width: '100%' }}
                                    />
                                </Box>
                            </Tooltip>
                        </Grid>
                    )}
                </Grid>

                <Box sx={stickyBar}>
                    <Button variant="outlined" onClick={handleCancel} sx={{ mr: 1 }}>
                        {localeMessages['cancel']}
                    </Button>
                    {canEdit && (
                        <Button variant="contained" color="secondary" onClick={save}>
                            {localeMessages['save_decision'] || 'Save Decision'}
                        </Button>
                    )}
                </Box>
            </Box>

            {/* Mounted on first visit and kept mounted after, so rule edits survive a tab switch. */}
            {contentIdentifier && branchingVisited && (
                <Box role="tabpanel" sx={{ display: activeTab === 'branching' ? 'block' : 'none' }}>
                    <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
                        <QuizBranching
                            key={branchingVersion}
                            courseId={courseId}
                            contentId={contentIdentifier}
                            options={savedOptions}
                            helpText={localeMessages['decision_branching_help']}
                            onChange={() => onBranchingChange?.()}
                        />
                    </Suspense>
                    <Box sx={stickyBar}>
                        <Button variant="outlined" onClick={handleCancel} sx={{ mr: 1 }}>
                            {localeMessages['back'] || localeMessages['cancel']}
                        </Button>
                    </Box>
                </Box>
            )}

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

export default DecisionForm;
