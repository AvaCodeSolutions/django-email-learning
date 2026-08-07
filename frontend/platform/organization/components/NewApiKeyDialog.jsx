import { useState } from 'react';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useAppContext } from '../../../src/render.jsx';

/**
 * Shown once, immediately after a key is created. The server stores only a
 * hash, so this is the only opportunity to copy the token — which is why the
 * key table deliberately offers no way to reveal it later.
 */
const NewApiKeyDialog = ({ token, onClose }) => {
    const { localeMessages } = useAppContext();
    const [copied, setCopied] = useState(false);

    const copyToken = async () => {
        try {
            await navigator.clipboard.writeText(token);
            setCopied(true);
        } catch (error) {
            console.error('Failed to copy API key:', error);
        }
    };

    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
                {localeMessages['new_api_key_created']}
            </Typography>
            <Alert severity="warning" sx={{ mb: 2 }}>
                {localeMessages['copy_key_now_warning']}
            </Alert>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
                <Typography
                    component="span"
                    data-testid="new-api-key-token"
                    sx={{ fontFamily: 'monospace', overflowWrap: 'anywhere', flex: 1 }}
                >
                    {token}
                </Typography>
                <IconButton size="small" onClick={copyToken} aria-label={localeMessages['copy'] || 'Copy'}>
                    <ContentCopyIcon fontSize="small" />
                </IconButton>
            </Box>
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 1 }}>
                {copied && <Typography variant="body2" color="success.main">{localeMessages['copied']}</Typography>}
                <Button variant="contained" onClick={onClose}>{localeMessages['done']}</Button>
            </Box>
        </Box>
    );
};

export default NewApiKeyDialog;
