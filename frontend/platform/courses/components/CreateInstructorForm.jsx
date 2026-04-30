import { useState } from 'react';
import { Alert, Box, Button } from '@mui/material';
import RequiredTextField from '../../../src/components/RequiredTextField';
import { useAppContext } from '../../../src/render.jsx';
import { getCookie } from '../../../src/utils';


const CreateInstructorForm = ({ onSuccess, activeOrganizationId }) => {
    const [email, setEmail] = useState('');
    const [emailHelperText, setEmailHelperText] = useState('');
    const [errorMessage, setErrorMessage] = useState('');
    const { localeMessages, apiBaseUrl } = useAppContext();

    const isValidEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

    const handleSubmit = () => {
        const trimmedEmail = email.trim();
        if (!trimmedEmail) {
            setEmailHelperText(localeMessages['email_required_helper_text']);
            return;
        }
        if (!isValidEmail(trimmedEmail)) {
            setEmailHelperText(localeMessages['invalid_email_helper_text']);
            return;
        }
        setEmailHelperText('');
        setErrorMessage('');

        fetch(`${apiBaseUrl}/users/get-or-create-by-email/`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ email: trimmedEmail, organization_id: activeOrganizationId }),
        })
            .then((response) => {
                if (!response.ok) throw new Error('Failed to get or create user');
                return response.json();
            })
            .then((userData) =>
                fetch(`${apiBaseUrl}/organizations/${activeOrganizationId}/users/`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({ user_id: userData.id, role: 'instructor' }),
                })
            )
            .then((response) => {
                if (!response.ok) throw new Error('Failed to add instructor to organization');
                return response.json();
            })
            .then((orgUserData) => {
                if (onSuccess) onSuccess(orgUserData);
                setEmail('');
            })
            .catch((error) => {
                console.error('Error adding instructor:', error);
                setErrorMessage(localeMessages['instructor_add_failed']);
            });
    };

    return (
        <Box>
            {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
            <RequiredTextField
                label={localeMessages['instructor_email']}
                helperText={emailHelperText}
                fullWidth
                margin="normal"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
            />
            <Button variant="contained" onClick={handleSubmit} sx={{ mt: 1, boxShadow: 'none' }}>
                {localeMessages['add_instructor']}
            </Button>
        </Box>
    );
};

export default CreateInstructorForm;
