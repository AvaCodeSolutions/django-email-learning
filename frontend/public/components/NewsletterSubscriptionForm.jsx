import { useState } from 'react';
import { getCookie } from '../../src/utils.js';
import { Alert, Box, Button, Checkbox, FormControlLabel, FormGroup, Stack, TextField, Typography } from '@mui/material';

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
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
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
        <Box sx={{ position: 'relative', mt: '57px' }}>
            <Box
                sx={{
                    position: 'absolute',
                    top: '40px',
                    left: '-24px',
                    right: '-24px',
                    bottom: '-32px',
                    zIndex: 0,
                    borderRadius: '0 0 8px 8px',
                    backgroundColor: '#fafafa',
                }}
            />
            <Box
                component="form"
                onSubmit={handleSubmit}
                sx={{
                    position: 'relative',
                    zIndex: 1,
                    py: { xs: 4, md: 7 },
                    px: { xs: 3, md: 6 },
                    mx: { xs: 2, md: '18%' },
                    borderRadius: 2,
                    backgroundColor: '#fefefe',
                    border: 'solid 1px #ededed50',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                }}
            >
                <Typography variant="h2" sx={{ mb: 1, fontSize: '1.25rem' }}>
                    {localeMessages['newsletters']}
                </Typography>
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                    {localeMessages['newsletter_subscribe_intro']}
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

                <Stack direction="row" spacing={0} sx={{ mb: 2, alignItems: 'flex-start' }}>
                    <TextField
                        label={localeMessages['email']}
                        type="email"
                        size="medium"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        error={!!emailError}
                        helperText={emailError}
                        fullWidth
                        required
                        sx={{
                            '& .MuiOutlinedInput-root': {
                                backgroundColor: '#fff',
                                borderTopLeftRadius: 8,
                                borderBottomLeftRadius: 8,
                                borderTopRightRadius: 0,
                                borderBottomRightRadius: 0,
                            },
                        }}
                    />

                    <Button
                        type="submit"
                        variant="contained"
                        disabled={submitting}
                        sx={{ flexShrink: 0, height: '56px', borderRadius: '0 8px 8px 0' }}
                    >
                        {localeMessages['newsletter_subscribe']}
                    </Button>
                </Stack>
            </Box>
        </Box>
    );
}
