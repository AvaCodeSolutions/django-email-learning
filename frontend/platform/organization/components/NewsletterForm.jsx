import { useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';

const NewsletterForm = ({ onClose, organizationId, refreshNewsletters }) => {
    const { localeMessages, apiBaseUrl: rawApiBaseUrl, languageOptions = [] } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const [title, setTitle] = useState('');
    const [language, setLanguage] = useState('en');
    const [titleError, setTitleError] = useState('');
    const [error, setError] = useState('');

    const validate = () => {
        setTitleError('');
        if (!title.trim()) {
            setTitleError(localeMessages['newsletter_title_required']);
            return false;
        }
        return true;
    };

    const handleSubmit = () => {
        if (!validate()) return;
        setError('');
        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/newsletters/`, { title: title.trim(), language })
            .then(() => {
                refreshNewsletters();
                onClose();
            })
            .catch(err => {
                if (err.status === 409) {
                    setError(localeMessages['newsletter_duplicate_error']);
                } else {
                    setError(localeMessages['newsletter_create_error']);
                }
            });
    };

    return (
        <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="h6">{localeMessages['create_newsletter']}</Typography>
            {error && <Typography color="error" variant="body2">{error}</Typography>}
            <TextField
                label={localeMessages['newsletter_title']}
                value={title}
                onChange={e => setTitle(e.target.value)}
                error={!!titleError}
                helperText={titleError}
                fullWidth
                required
            />
            <FormControl fullWidth>
                <InputLabel>{localeMessages['newsletter_language']}</InputLabel>
                <Select
                    value={language}
                    label={localeMessages['newsletter_language']}
                    onChange={e => setLanguage(e.target.value)}
                >
                    {languageOptions.map(opt => (
                        <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                </Select>
            </FormControl>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                <Button onClick={onClose}>{localeMessages['cancel']}</Button>
                <Button variant="contained" onClick={handleSubmit}>{localeMessages['create_newsletter']}</Button>
            </Box>
        </Box>
    );
};

export default NewsletterForm;
