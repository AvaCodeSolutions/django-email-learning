import { useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { getCookie } from '../../../src/utils.js';
import { useAppContext } from '../../../src/render.jsx';


const UserForm = ({ onClose, organizationId, refreshUsers, user = null }) => {
    const { localeMessages, apiBaseUrl } = useAppContext();
    const [email, setEmail] = useState(user ? user.email : '');
    const [role, setRole] = useState(user ? user.role : 'viewer');
    const [error, setError] = useState('');

    const createUser = (id) => {
        fetch(`${apiBaseUrl}/organizations/${organizationId}/users/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ 'user_id': id, 'role': role }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to add user to organization');
            }
            return response.json();
        })
        .then(data => {
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
        if (user) {
            updateUser();
        } else {
            addUser();
        }

    };

    const addUser = () => {
        fetch(`${apiBaseUrl}/users/get-or-create-by-email/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ 'email': email, 'organization_id': organizationId }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to get or create user by email');
            }
            return response.json();
        })
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
        fetch(`${apiBaseUrl}/organizations/${organizationId}/users/${user.user_id}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ 'role': role }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to update user role');
            }
            return response.json();
        })
        .then(data => {
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
            <FormControl fullWidth>
                <InputLabel id="role-label">{localeMessages["role"]}</InputLabel>
                <Select
                    labelId="role-label"
                    value={role}
                    label={localeMessages["role"]}
                    onChange={(e) => setRole(e.target.value)}
                >
                    <MenuItem value="viewer">{localeMessages["viewer"]}</MenuItem>
                    <MenuItem value="editor">{localeMessages["editor"]}</MenuItem>
                    <MenuItem value="admin">{localeMessages["admin"]}</MenuItem>
                </Select>
            </FormControl>
            {error && <Typography color="error">{error}</Typography>}
            <Button type="submit" variant="contained" color="secondary">
                {  user ? localeMessages["edit_user"] : localeMessages["add_user"]}
            </Button>
        </Box>
    );
};

export default UserForm;
