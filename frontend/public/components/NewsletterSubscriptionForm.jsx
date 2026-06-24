import { useState } from 'react';
import { Alert, Box, Button, Checkbox, FormControlLabel, FormGroup, TextField, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';

export default function NewsletterSubscriptionForm({ newsletters, subscribeApiUrl, localeMessages }) {
    const [email, setEmail] = useState('');
    const [checkedIds, setCheckedIds] = useState(() => Object.fromEntries(newsletters.map(n => [n.id, true])));
    const [emailError, setEmailError] = useState('');
    const [status, setStatus] = useState(null); // 'success' | 'error' | null
    const [submitting, setSubmitting] = useState(false);

    const toggleNewsletter = (id) => {
        setCheckedIds(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setEmailError('');
        setStatus(null);

        if (!email.trim()) {
            setEmailError(localeMessages['email_required']);
            return;
        }

        const selectedIds = newsletters.filter(n => checkedIds[n.id]).map(n => n.id);
        if (selectedIds.length === 0) {
            setStatus('select_one');
            return;
        }

        setSubmitting(true);
        try {
            const res = await fetch(subscribeApiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim(), newsletter_ids: selectedIds }),
            });
            if (res.ok) {
                setStatus('success');
                setEmail('');
            } else {
                setStatus('error');
            }
        } catch {
            setStatus('error');
        } finally {
            setSubmitting(false);
        }
    };

    if (status === 'success') {
        return (
            <Alert severity="success" sx={{ mt: 2 }}>
                {localeMessages['newsletter_subscribe_success']}
            </Alert>
        );
    }

    return (
        <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{
                p: { xs: 2, md: 3 },
                mt: 4,
                borderRadius: 2,
                backgroundColor: (theme) => alpha(theme.palette.primary.main, 0.05),
            }}
        >
            <Typography variant="h2" sx={{ mb: 2, fontSize: '1.25rem' }}>
                {localeMessages['newsletters']}
            </Typography>

            {status === 'error' && (
                <Alert severity="error" sx={{ mb: 2 }}>{localeMessages['newsletter_subscribe_error']}</Alert>
            )}
            {status === 'select_one' && (
                <Alert severity="warning" sx={{ mb: 2 }}>{localeMessages['newsletter_select_one']}</Alert>
            )}

            <FormGroup sx={{ mb: 2 }}>
                {newsletters.map(n => (
                    <FormControlLabel
                        key={n.id}
                        control={
                            <Checkbox
                                checked={!!checkedIds[n.id]}
                                onChange={() => toggleNewsletter(n.id)}
                            />
                        }
                        label={n.title}
                    />
                ))}
            </FormGroup>

            <TextField
                label={localeMessages['email']}
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                error={!!emailError}
                helperText={emailError}
                fullWidth
                required
                sx={{ mb: 2 }}
            />

            <Button type="submit" variant="contained" disabled={submitting}>
                {localeMessages['newsletter_subscribe']}
            </Button>
        </Box>
    );
}
