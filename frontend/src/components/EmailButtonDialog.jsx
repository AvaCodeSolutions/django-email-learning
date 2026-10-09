import { useState } from 'react';
import {
    Box,
    Button,
    Checkbox,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    FormControlLabel,
    TextField,
    Typography,
} from '@mui/material';
import { sanitizeUrl } from '../sanitizeUrl.js';
import { LINK_VARIABLES, PARAM_NAME_PATTERN, exampleUrl, parseQueryParams, serializeQueryParams } from './emailButton.js';

const initialState = (button, variables) => {
    const saved = parseQueryParams(button?.queryParams);
    return {
        label: button?.label || '',
        href: button?.href || '',
        params: variables.map((variable) => {
            const existing = saved.find((param) => param.variable === variable);
            return { variable, enabled: Boolean(existing), name: existing?.name || variable };
        }),
    };
};

/**
 * Inserts or edits a button in the content editor: its text, the page it links to, and
 * which of the learner's details are added to that link when the email is sent.
 *
 * `button` is the attributes of the button being edited, or null for a new one;
 * `variables` the link variables this content can offer - a newsletter has no enrollment.
 */
function EmailButtonDialog({ open, button, variables, onSave, onRemove, onClose }) {
    const [form, setForm] = useState(() => initialState(button, variables));
    const [errors, setErrors] = useState({});

    const updateParam = (variable, changes) => {
        setForm((current) => ({
            ...current,
            params: current.params.map((param) => (param.variable === variable ? { ...param, ...changes } : param)),
        }));
    };

    const enabledParams = form.params.filter((param) => param.enabled).map(({ name, variable }) => ({ name: name.trim(), variable }));
    const href = sanitizeUrl(form.href.trim(), '');
    const preview = href ? exampleUrl(href, enabledParams) : '';

    const save = () => {
        const nextErrors = {};
        if (!form.label.trim()) {
            nextErrors.label = 'A button needs some text.';
        }
        if (!/^https?:\/\//i.test(form.href.trim()) || !href) {
            nextErrors.href = 'Enter a full web address, starting with https://';
        }
        const names = enabledParams.map((param) => param.name);
        enabledParams.forEach(({ name, variable }) => {
            if (!PARAM_NAME_PATTERN.test(name)) {
                nextErrors[variable] = 'Use letters, numbers, dots, hyphens and underscores only.';
            } else if (names.filter((other) => other === name).length > 1) {
                nextErrors[variable] = 'Each detail needs its own parameter name.';
            }
        });
        setErrors(nextErrors);
        if (Object.keys(nextErrors).length > 0) {
            return;
        }
        onSave({ label: form.label.trim(), href, queryParams: serializeQueryParams(enabledParams) });
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>{button ? 'Edit Button' : 'Insert Button'}</DialogTitle>
            <DialogContent>
                <TextField
                    autoFocus
                    margin="dense"
                    label="Button text"
                    fullWidth
                    value={form.label}
                    onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))}
                    error={Boolean(errors.label)}
                    helperText={errors.label}
                    slotProps={{ htmlInput: { maxLength: 100 } }}
                />
                <TextField
                    margin="dense"
                    label="Link"
                    type="url"
                    fullWidth
                    placeholder="https://"
                    value={form.href}
                    onChange={(event) => setForm((current) => ({ ...current, href: event.target.value }))}
                    error={Boolean(errors.href)}
                    helperText={errors.href}
                />

                {variables.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                        <Typography variant="subtitle2">Add learner details to the link</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            When the email is sent, each learner&apos;s own details are added to the end of the link,
                            so the page it opens knows who clicked - for example to match a payment to their enrollment.
                            A detail that isn&apos;t available, such as the enrollment when you send a lesson to yourself,
                            is left off.
                        </Typography>
                        {form.params.map((param) => (
                            <Box key={param.variable} sx={{ mb: 1 }}>
                                <FormControlLabel
                                    control={(
                                        <Checkbox
                                            checked={param.enabled}
                                            onChange={(event) => updateParam(param.variable, { enabled: event.target.checked })}
                                        />
                                    )}
                                    label={LINK_VARIABLES[param.variable].label}
                                />
                                <Typography variant="caption" color="text.secondary" component="p" sx={{ ml: 4, mt: -0.5 }}>
                                    {LINK_VARIABLES[param.variable].description}
                                </Typography>
                                {param.enabled && (
                                    <TextField
                                        size="small"
                                        margin="dense"
                                        label="Parameter name"
                                        value={param.name}
                                        onChange={(event) => updateParam(param.variable, { name: event.target.value })}
                                        error={Boolean(errors[param.variable])}
                                        helperText={errors[param.variable] || 'Change it if the page expects another name, e.g. client_reference_id for a Stripe payment link.'}
                                        slotProps={{ htmlInput: { maxLength: 64, style: { fontFamily: 'monospace' } } }}
                                        sx={{ ml: 4, width: 'calc(100% - 32px)' }}
                                    />
                                )}
                            </Box>
                        ))}
                    </Box>
                )}

                {preview && enabledParams.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">A learner&apos;s link will look like:</Typography>
                        <Typography
                            data-testid="email-button-preview"
                            variant="body2"
                            sx={{ fontFamily: 'monospace', wordBreak: 'break-all', p: 1, borderRadius: 1, backgroundColor: 'action.hover' }}
                        >
                            {preview}
                        </Typography>
                    </Box>
                )}
            </DialogContent>
            <DialogActions>
                {button && onRemove && (
                    <Button color="error" onClick={onRemove} sx={{ mr: 'auto' }}>Remove</Button>
                )}
                <Button onClick={onClose}>Cancel</Button>
                <Button onClick={save} variant="contained">{button ? 'Save' : 'Insert'}</Button>
            </DialogActions>
        </Dialog>
    );
}

export default EmailButtonDialog;
