import { Container, Typography, Button, Box } from '@mui/material';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';

const DeleteNewsletterDialog = ({ newsletter, onClose, onSuccess }) => {
    const { localeMessages, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);

    const handleDelete = () => {
        apiClient.del(`${apiBaseUrl}/organizations/${newsletter.organization_id}/newsletters/${newsletter.id}/`)
            .then(() => {
                onSuccess();
                onClose();
            })
            .catch(error => console.error('Error deleting newsletter:', error));
    };

    return (
        <Container sx={{ padding: 4, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
                {localeMessages["newsletter_delete_confirmation"].replace("NEWSLETTER_TITLE", newsletter.title)}
            </Typography>
            <Box sx={{ marginTop: 2 }}>
                <Button variant="contained" color="error" onClick={handleDelete} sx={{ marginRight: 2 }}>
                    {localeMessages["delete"]}
                </Button>
                <Button variant="outlined" onClick={onClose}>
                    {localeMessages["cancel"]}
                </Button>
            </Box>
        </Container>
    );
};

export default DeleteNewsletterDialog;
