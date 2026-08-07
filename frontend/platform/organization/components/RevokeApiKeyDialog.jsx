import { Container, Typography, Button, Box } from '@mui/material';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';

const RevokeApiKeyDialog = ({ apiKey, organizationId, onClose, onSuccess }) => {
    const { localeMessages, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);

    const handleRevoke = () => {
        apiClient.del(`${apiBaseUrl}/organizations/${organizationId}/api-keys/${apiKey.id}/`)
            .then(() => {
                onSuccess();
                onClose();
            })
            .catch(error => console.error('Error revoking API key:', error));
    };

    return (
        <Container sx={{ padding: 4, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
                {localeMessages['confirm_revocation']}
            </Typography>
            <Typography>
                {localeMessages['are_you_sure_revoke_key'].replace('API_KEY_NAME', apiKey.name)}
            </Typography>
            <Box sx={{ marginTop: 2 }}>
                <Button variant="contained" color="error" onClick={handleRevoke} sx={{ marginRight: 2 }}>
                    {localeMessages['revoke']}
                </Button>
                <Button variant="outlined" onClick={onClose}>
                    {localeMessages['cancel']}
                </Button>
            </Box>
        </Container>
    );
};

export default RevokeApiKeyDialog;
