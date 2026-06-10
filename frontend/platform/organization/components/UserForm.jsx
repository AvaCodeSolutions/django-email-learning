import { useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';


const UserForm = ({ onClose, organizationId, refreshUsers, user = null }) => {
    const { localeMessages, apiBaseUrl } = useAppContext();
    const [email, setEmail] = useState(user ? user.email : '');
    const [role, setRole] = useState(user ? user.role : 'viewer');
    const [displayName, setDisplayName] = useState(user ? (user.display_name || '') : '');
    const [displayNameError, setDisplayNameError] = useState('');
    const [photoUrl, setPhotoUrl] = useState(user? user.photo_url : null);
    const [photoPath, setPhotoPath] = useState(user ? (user.photo || null) : null);
    const [error, setError] = useState('');

    const roleDescriptionByRole = {
        viewer: localeMessages["viewer_role_description"],
        editor: localeMessages["editor_role_description"],
        instructor: localeMessages["instructor_role_description"],
        admin: localeMessages["admin_role_description"],
    };

    const selectedRoleDescription = roleDescriptionByRole[role] || '';

    const validateForm = () => {
        setError('');

        if (role === 'instructor' && !displayName.trim()) {
            setDisplayNameError(localeMessages['display_name_required']);
            return false;
        }

        setDisplayNameError('');
        return true;
    };

    const createUser = (id) => {
        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/users/`, {
            'user_id': id,
            'role': role,
            'display_name': displayName.trim() || null,
            'photo': photoPath,
        })
        .then(() => {
            refreshUsers();
            onClose();
        })
        .catch(error => {
            console.error('Error adding user to organization:', error);
            setError(localeMessages["failed_to_add_user"]);
        });
    }

    const handleSubmit = (event) => {
        event.preventDefault();
        if (!validateForm()) {
            return;
        }
        if (user) {
            updateUser();
        } else {
            addUser();
        }

    };

    const addUser = () => {
        apiClient.post(`${apiBaseUrl}/users/get-or-create-by-email/`, { 'email': email, 'organization_id': organizationId })
        .then(data => {
            const userId = data.id;
            createUser(userId);
        })
        .catch(error => {
            console.error('Error getting or creating user:', error);
            setError(localeMessages["failed_to_get_or_create_user"]);
        });
    }

    const updateUser = () => {
        console.log('Updating user:', user);
        const payload = {
            'role': role ,
            display_name: displayName.trim() || null,
            photo: photoPath,
        };

        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/users/${user.user_id}/`, payload)
        .then(() => {
            refreshUsers();
            onClose();
        })
        .catch(error => {
            console.error('Error updating user role:', error);
            setError(localeMessages["failed_to_update_user_role"]);
        });
    }

    return (
        <Box component="form" onSubmit={handleSubmit} sx={{ p:4, gap: 2, display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6">{  user ? localeMessages["change_user_role"] : localeMessages["add_users_to_organization"]}</Typography>
            <TextField
                label={localeMessages["email"]}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={!!user}
            />
            <TextField
                label={localeMessages["display_name"]}
                value={displayName}
                onChange={(e) => {
                    setDisplayName(e.target.value);
                    if (displayNameError) {
                        setDisplayNameError('');
                    }
                }}
                required={role === 'instructor'}
                error={Boolean(displayNameError)}
                helperText={displayNameError}
            />
            <FormControl fullWidth>
                <InputLabel id="role-label">{localeMessages["role"]}</InputLabel>
                <Select
                    labelId="role-label"
                    value={role}
                    label={localeMessages["role"]}
                    onChange={(e) => {
                        setRole(e.target.value);
                        if (e.target.value !== 'instructor') {
                            setDisplayNameError('');
                        }
                    }}
                >
                    <MenuItem value="viewer">{localeMessages["viewer"]}</MenuItem>
                    <MenuItem value="editor">{localeMessages["editor"]}</MenuItem>
                    <MenuItem value="instructor">{localeMessages["instructor"]}</MenuItem>
                    <MenuItem value="admin">{localeMessages["admin"]}</MenuItem>
                </Select>
            </FormControl>
            {selectedRoleDescription && (
                <Typography variant="body2" color="text.secondary">
                    {selectedRoleDescription}
                </Typography>
            )}
            <Box>
                <Typography variant="body2" sx={{ mb: 1 }}>
                    {localeMessages["photo"]}
                </Typography>
                <ImageUpload
                    initialUrl={photoUrl}
                    onUploadSuccess={(data) => {
                        setPhotoUrl(data.file_url);
                        setPhotoPath(data.file_path);
                    }}
                    onUploadError={() => {
                        setError(localeMessages["failed_to_add_user"]);
                    }}
                />
            </Box>

            {error && <Typography color="error">{error}</Typography>}
            <Button type="submit" variant="contained" color="secondary">
                {  user ? localeMessages["edit_user"] : localeMessages["add_user"]}
            </Button>
        </Box>
    );
};

export default UserForm;
