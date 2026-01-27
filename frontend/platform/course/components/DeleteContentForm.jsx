import { Container, Typography, Button, Box } from '@mui/material';

const DeleteContentForm = ({ content, onDelete, onCancel }) => {
    return (
        <Container sx={{ padding: 4, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
                {localeMessages["delete_content_confirmation"].replace("CONTENT_TITLE", content.title)}
            </Typography>
            <Box sx={{ marginTop: 2 }}>
                <Button variant="contained" color="error" onClick={() => onDelete(content.id)} sx={{ marginRight: 2 }}>
                    {localeMessages["delete"]}
                </Button>
                <Button variant="outlined" onClick={onCancel}>
                    {localeMessages["cancel"]}
                </Button>
            </Box>
        </Container>
    );
}

export default DeleteContentForm;
