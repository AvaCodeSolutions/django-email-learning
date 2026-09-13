import { useEffect, useState } from 'react';
import { Alert, Box, Button, IconButton, LinearProgress, MenuItem, TextField, Tooltip, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import DeleteIcon from '@mui/icons-material/Delete';
import { useAppContext } from '../../../src/render';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';
import { THRESHOLD_CONDITIONS, TRANSITION_CONDITIONS, errorMessageFrom } from './branching.js';

const toEditable = (transitions) => transitions.map((rule) => ({
    condition: rule.condition,
    threshold: rule.threshold ?? '',
    target_id: rule.target_id,
}));

/**
 * The routing rules on one quiz, edited as a list and saved as a whole.
 *
 * The server replaces the full set on save, so rules can be reordered freely here - the order
 * is what decides which rule matches first.
 */
const QuizBranching = ({ courseId, contentId, onChange }) => {
    const { localeMessages, userRole, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');
    const courseUrl = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}`;
    const canEdit = userRole === 'admin' || userRole === 'editor';

    const [loading, setLoading] = useState(true);
    const [tracks, setTracks] = useState([]);
    const [rules, setRules] = useState([]);
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        Promise.all([
            apiClient.get(`${courseUrl}/tracks/`),
            apiClient.get(`${courseUrl}/contents/${contentId}/transitions/`),
        ])
            .then(([trackData, ruleData]) => {
                setTracks(trackData.tracks || []);
                setRules(toEditable(ruleData.transitions || []));
            })
            .catch((error) => {
                console.error('Error loading routing rules:', error);
                setErrorMessage(localeMessages['branching_load_failed'] || 'Could not load the routing rules.');
            })
            .finally(() => setLoading(false));
    }, [courseUrl, contentId, localeMessages]);

    const edit = (change) => {
        setSuccessMessage('');
        setRules(change);
    };

    const updateRule = (index, changes) => edit((current) => current.map((rule, position) => {
        if (position !== index) {
            return rule;
        }
        const next = { ...rule, ...changes };
        if ('condition' in changes) {
            next.threshold = THRESHOLD_CONDITIONS.has(changes.condition)
                ? (rule.threshold === '' ? 50 : rule.threshold)
                : '';
        }
        return next;
    }));

    const addRule = () => edit((current) => {
        const rule = { condition: 'failed', threshold: '', target_id: tracks[0].id };
        // An otherwise rule matches everything, so anything after it could never match.
        const last = current[current.length - 1];
        if (last && last.condition === 'default') {
            return [...current.slice(0, -1), rule, last];
        }
        return [...current, rule];
    });

    const moveRule = (index, offset) => edit((current) => {
        const target = index + offset;
        if (target < 0 || target >= current.length) {
            return current;
        }
        const next = [...current];
        [next[index], next[target]] = [next[target], next[index]];
        return next;
    });

    const removeRule = (index) => edit((current) => current.filter((_, position) => position !== index));

    const save = () => {
        setErrorMessage('');
        setSuccessMessage('');
        const missingThreshold = rules.some((rule) => THRESHOLD_CONDITIONS.has(rule.condition)
            && (rule.threshold === '' || Number(rule.threshold) < 0 || Number(rule.threshold) > 100));
        if (missingThreshold) {
            setErrorMessage(localeMessages['rule_threshold_required'] || 'A score rule needs a score between 0 and 100.');
            return;
        }
        setSaving(true);
        apiClient.put(`${courseUrl}/contents/${contentId}/transitions/`, {
            transitions: rules.map((rule) => ({
                condition: rule.condition,
                threshold: THRESHOLD_CONDITIONS.has(rule.condition) ? Number(rule.threshold) : null,
                target_id: Number(rule.target_id),
            })),
        })
            .then((data) => {
                const saved = data.transitions || [];
                setRules(toEditable(saved));
                setSuccessMessage(localeMessages['rules_saved'] || 'Routing rules saved.');
                onChange?.(saved.length);
            })
            .catch((error) => {
                console.error('Error saving routing rules:', error);
                setErrorMessage(errorMessageFrom(error, localeMessages['rules_save_failed'] || 'Could not save the routing rules.'));
            })
            .finally(() => setSaving(false));
    };

    if (loading) {
        return <Box sx={{ p: 2 }}><LinearProgress /></Box>;
    }

    return (
        <Box>
            {localeMessages['branching_rules_help'] && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {localeMessages['branching_rules_help']}
                </Typography>
            )}
            {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
            {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}
            {tracks.length === 0 ? (
                <Alert severity="info">{localeMessages['branching_no_tracks']}</Alert>
            ) : (
                <>
                    {rules.map((rule, index) => (
                        <Box
                            key={index}
                            data-testid="routing-rule"
                            sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, mb: 1.5 }}
                        >
                            <TextField
                                select
                                size="small"
                                id={`rule-condition-${index}`}
                                label={localeMessages['rule_condition'] || 'When'}
                                value={rule.condition}
                                onChange={(event) => updateRule(index, { condition: event.target.value })}
                                disabled={!canEdit}
                                sx={{ minWidth: 170 }}
                            >
                                {TRANSITION_CONDITIONS.map((condition) => (
                                    <MenuItem key={condition} value={condition}>
                                        {localeMessages[`condition_${condition}`] || condition}
                                    </MenuItem>
                                ))}
                            </TextField>
                            {THRESHOLD_CONDITIONS.has(rule.condition) && (
                                <TextField
                                    size="small"
                                    type="number"
                                    id={`rule-threshold-${index}`}
                                    label={localeMessages['rule_threshold'] || 'Score'}
                                    value={rule.threshold}
                                    onChange={(event) => updateRule(index, { threshold: event.target.value })}
                                    disabled={!canEdit}
                                    slotProps={{ htmlInput: { min: 0, max: 100 } }}
                                    sx={{ width: 100 }}
                                />
                            )}
                            <TextField
                                select
                                size="small"
                                id={`rule-target-${index}`}
                                label={localeMessages['rule_target'] || 'Send to'}
                                value={rule.target_id}
                                onChange={(event) => updateRule(index, { target_id: event.target.value })}
                                disabled={!canEdit}
                                sx={{ minWidth: 200 }}
                            >
                                {tracks.map((track) => (
                                    <MenuItem key={track.id} value={track.id}>{track.name}</MenuItem>
                                ))}
                            </TextField>
                            {canEdit && (
                                <Box sx={{ display: 'flex' }}>
                                    <Tooltip title={localeMessages['move_rule_up'] || 'Move rule up'}>
                                        <span>
                                            <IconButton size="small" aria-label={localeMessages['move_rule_up'] || 'Move rule up'} disabled={index === 0} onClick={() => moveRule(index, -1)}>
                                                <ArrowUpwardIcon fontSize="small" />
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                    <Tooltip title={localeMessages['move_rule_down'] || 'Move rule down'}>
                                        <span>
                                            <IconButton size="small" aria-label={localeMessages['move_rule_down'] || 'Move rule down'} disabled={index === rules.length - 1} onClick={() => moveRule(index, 1)}>
                                                <ArrowDownwardIcon fontSize="small" />
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                    <Tooltip title={localeMessages['remove_rule'] || 'Remove rule'}>
                                        <IconButton size="small" aria-label={localeMessages['remove_rule'] || 'Remove rule'} onClick={() => removeRule(index)}>
                                            <DeleteIcon fontSize="small" />
                                        </IconButton>
                                    </Tooltip>
                                </Box>
                            )}
                        </Box>
                    ))}
                    {canEdit && (
                        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                            <Button variant="outlined" startIcon={<AddIcon />} onClick={addRule}>
                                {localeMessages['add_rule'] || 'Add rule'}
                            </Button>
                            <Button variant="contained" color="secondary" onClick={save} disabled={saving}>
                                {localeMessages['save_rules'] || 'Save rules'}
                            </Button>
                        </Box>
                    )}
                </>
            )}
        </Box>
    );
};

export default QuizBranching;
