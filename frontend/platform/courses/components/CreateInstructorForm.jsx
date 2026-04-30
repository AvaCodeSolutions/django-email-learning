import { useState } from 'react';
import { Alert, Box, Button, Typography } from '@mui/material';
import RequiredTextField from '../../../src/components/RequiredTextField';
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useAppContext } from '../../../src/render.jsx';
import { getCookie } from '../../../src/utils';


const CreateInstructorForm = ({ onSuccess, activeOrganizationId }) => {
    const [email, setEmail] = useState('');
    const [emailHelperText, setEmailHelperText] = useState('');
    const [displayName, setDisplayName] = useState('');
    const [displayNameHelperText, setDisplayNameHelperText] = useState('');
    const [photoPath, setPhotoPath] = useState(null);
    const [photoUrl, setPhotoUrl] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');
    const { localeMessages, apiBaseUrl } = useAppContext();

    const isValidEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

    const handleSubmit = () => {
        const trimmedEmail = email.trim();
        const trimmedDisplayName = displayName.trim();
        let valid = true;

        if (!trimmedEmail) {
            setEmailHelperText(localeMessages['email_required_helper_text']);
            valid = false;
        } else if (!isValidEmail(trimmedEmail)) {
            setEmailHelperText(localeMessages['invalid_email_helper_text']);
            valid = false;
        } else {
            setEmailHelperText('');
        }

        if (!trimmedDisplayName) {
            setDisplayNameHelperText(localeMessages['instructor_display_name_required']);
            valid = false;
        } else {
            setDisplayNameHelperText('');
        }

        if (!valid) return;
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
                    body: JSON.stringify({
                        user_id: userData.id,
                        role: 'instructor',
                        display_name: trimmedDisplayName,
                        photo: photoPath,
                    }),
                })
            )
            .then((response) => {
                if (!response.ok) throw new Error('Failed to add instructor to organization');
                return response.json();
            })
            .then((orgUserData) => {
                if (onSuccess) onSuccess(orgUserData);
                setEmail('');
                setDisplayName('');
                setPhotoPath(null);
                setPhotoUrl(null);
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
            <RequiredTextField
                label={localeMessages['instructor_display_name']}
                helperText={displayNameHelperText}
                fullWidth
                margin="normal"
                value={displayName}
                onChange={(e) => {
                    setDisplayName(e.target.value);
                    if (displayNameHelperText) setDisplayNameHelperText('');
                }}
            />
            <Typography variant="body2" sx={{ mt: 1, mb: 0.5 }}>
                {localeMessages['instructor_photo']}
            </Typography>
            <ImageUpload
                initialUrl={photoUrl}
                onUploadSuccess={(data) => {
                    setPhotoUrl(data.file_url);
                    setPhotoPath(data.file_path);
                }}
                onUploadError={() => setErrorMessage(localeMessages['instructor_add_failed'])}
            />

            <Button variant="contained" onClick={handleSubmit} sx={{ mt: 1, boxShadow: 'none', display: 'block', ml: 'auto' }}>
                {localeMessages['add_instructor']}
            </Button>

        </Box>
    );
};

export default CreateInstructorForm;
