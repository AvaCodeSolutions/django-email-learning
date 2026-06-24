import { useState, useEffect } from 'react';
import {
    Accordion, AccordionDetails, AccordionSummary, Box, Button,
    FormControl, InputLabel, MenuItem, Select, TextField, Typography, Alert,
} from '@mui/material';
import { useAppContext } from '../../../src/render.jsx';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlusIcon from '@mui/icons-material/Add';
import apiClient from '../../../src/apiClient.js';

function AddNewsletterForm({ onChangeCallback, activeOrganizationId, initialNewsletterIdId = null, showCreate = true }) {
    const [newsletters, setNewsletters] = useState([]);
    const [newsletterId, setNewsletterId] = useState(initialNewsletterIdId);
    const [expanded, setExpanded] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [newLanguage, setNewLanguage] = useState('en');
    const [creating, setCreating] = useState(false);
    const [createError, setCreateError] = useState('');
    const { localeMessages, apiBaseUrl, languageOptions = [] } = useAppContext();

    const hasNewsletters = newsletters.length > 0;

    useEffect(() => {
        apiClient.get(`${apiBaseUrl}/organizations/${activeOrganizationId}/newsletters/`)
            .then(data => {
                setNewsletters(data.newsletters || []);
                if ((data.newsletters || []).length === 0) {
                    setExpanded(true);
                }
            })
            .catch(err => console.error('Error fetching newsletters:', err));
    }, []);

    const handleSelect = (id) => {
        setNewsletterId(id);
        if (onChangeCallback) onChangeCallback(id);
    };

    const handleCreate = () => {
        if (!newTitle.trim()) return;
        setCreating(true);
        setCreateError('');
        apiClient.post(`${apiBaseUrl}/organizations/${activeOrganizationId}/newsletters/`, {
            title: newTitle.trim(),
            language: newLanguage,
        })
            .then(data => {
                const updated = [...newsletters, data];
                setNewsletters(updated);
                setNewsletterId(data.id);
                if (onChangeCallback) onChangeCallback(data.id);
                setExpanded(false);
                setNewTitle('');
            })
            .catch(() => setCreateError(localeMessages['newsletter_create_error'] || 'Failed to create newsletter.'))
            .finally(() => setCreating(false));
    };

    return (
        <div>
            {hasNewsletters && (
                <FormControl sx={{ mb: 2, minWidth: '100%' }}>
                    <InputLabel id="newsletter-select-label">{localeMessages['newsletter']}</InputLabel>
                    <Select
                        labelId="newsletter-select-label"
                        label={localeMessages['newsletter']}
                        value={newsletterId || ''}
                        onChange={e => handleSelect(e.target.value || null)}
                    >
                        <MenuItem value="">{localeMessages['none']}</MenuItem>
                        {newsletters.map(n => (
                            <MenuItem key={n.id} value={n.id} style={{ fontWeight: n.id === newsletterId ? 'bold' : 'normal' }}>
                                {n.title}
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>
            )}
            {showCreate && <Accordion expanded={expanded} onChange={() => hasNewsletters && setExpanded(!expanded)}>
                <AccordionSummary expandIcon={hasNewsletters ? <ExpandMoreIcon /> : null}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PlusIcon />
                        <Typography component="span">{localeMessages['new_newsletter']}</Typography>
                    </Box>
                </AccordionSummary>
                <AccordionDetails>
                    {createError && <Alert severity="error" sx={{ mb: 1 }}>{createError}</Alert>}
                    <TextField
                        label={localeMessages['newsletter_title'] || 'Title'}
                        value={newTitle}
                        onChange={e => setNewTitle(e.target.value)}
                        fullWidth
                        size="small"
                        sx={{ mb: 1.5 }}
                    />
                    <FormControl fullWidth size="small" sx={{ mb: 1.5 }}>
                        <InputLabel>{localeMessages['newsletter_language'] || 'Language'}</InputLabel>
                        <Select
                            label={localeMessages['newsletter_language'] || 'Language'}
                            value={newLanguage}
                            onChange={e => setNewLanguage(e.target.value)}
                        >
                            {languageOptions.map(opt => (
                                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <Button
                        variant="contained"
                        size="small"
                        disabled={creating || !newTitle.trim()}
                        onClick={handleCreate}
                    >
                        {localeMessages['add'] || 'Add'}
                    </Button>
                </AccordionDetails>
            </Accordion>}
        </div>
    );
}

export default AddNewsletterForm;
