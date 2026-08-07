import { useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormGroup from '@mui/material/FormGroup';
import FormLabel from '@mui/material/FormLabel';
import FormHelperText from '@mui/material/FormHelperText';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';

const ApiKeyForm = ({ onClose, organizationId, onCreated }) => {
    const { localeMessages, apiBaseUrl: rawApiBaseUrl, apiKeyScopes = [] } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const [name, setName] = useState('');
    const [selectedScopes, setSelectedScopes] = useState([]);
    const [expiresAt, setExpiresAt] = useState('');
    const [nameError, setNameError] = useState('');
    const [scopesError, setScopesError] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const toggleScope = (value) => {
        setSelectedScopes(current =>
            current.includes(value) ? current.filter(scope => scope !== value) : [...current, value]
        );
    };

    const validate = () => {
        setNameError('');
        setScopesError('');
        let valid = true;
        if (!name.trim()) {
            setNameError(localeMessages['api_key_name_required']);
            valid = false;
        }
        // The API rejects a scopeless key too; checking here saves a round trip
        // and puts the message next to the field.
        if (selectedScopes.length === 0) {
            setScopesError(localeMessages['api_key_scopes_required']);
            valid = false;
        }
        return valid;
    };

    const handleSubmit = () => {
        if (!validate()) return;
        setError('');
        setSubmitting(true);

        const payload = { name: name.trim(), scopes: selectedScopes };
        if (expiresAt) {
            // The field is a date; the API takes a datetime.
            payload.expires_at = `${expiresAt}T00:00:00Z`;
        }

        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/api-keys/`, payload)
            .then(data => onCreated(data))
            .catch(() => {
                setError(localeMessages['api_key_create_error']);
                setSubmitting(false);
            });
    };

    return (
        <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="h6">{localeMessages['create_api_key']}</Typography>
            {error && <Typography color="error" variant="body2">{error}</Typography>}

            <TextField
                label={localeMessages['api_key_name']}
                value={name}
                onChange={e => setName(e.target.value)}
                error={!!nameError}
                helperText={nameError}
                slotProps={{ htmlInput: { maxLength: 100 } }}
                fullWidth
                required
            />

            <FormControl error={!!scopesError} component="fieldset" variant="standard">
                <FormLabel component="legend">{localeMessages['api_key_scopes']}</FormLabel>
                <FormGroup>
                    {apiKeyScopes.map(scope => (
                        <FormControlLabel
                            key={scope.value}
                            control={
                                <Checkbox
                                    checked={selectedScopes.includes(scope.value)}
                                    onChange={() => toggleScope(scope.value)}
                                />
                            }
                            label={`${scope.label} (${scope.value})`}
                        />
                    ))}
                </FormGroup>
                {scopesError && <FormHelperText>{scopesError}</FormHelperText>}
            </FormControl>

            <TextField
                label={localeMessages['api_key_expires_at']}
                type="date"
                value={expiresAt}
                onChange={e => setExpiresAt(e.target.value)}
                helperText={localeMessages['api_key_expires_at_helper_text']}
                slotProps={{ inputLabel: { shrink: true } }}
                fullWidth
            />

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                <Button onClick={onClose}>{localeMessages['cancel']}</Button>
                <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
                    {localeMessages['create_api_key']}
                </Button>
            </Box>
        </Box>
    );
};

export default ApiKeyForm;
