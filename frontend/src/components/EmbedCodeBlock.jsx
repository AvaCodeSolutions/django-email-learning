import { Box, Typography, Tooltip, IconButton } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

export default function EmbedCodeBlock({ label, code, copied, onCopy, copyLabel, copiedLabel }) {
    return (
        <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>{label}</Typography>
            <Box sx={{ position: 'relative' }}>
                <Box
                    component="pre"
                    sx={{
                        backgroundColor: '#f4f4f4',
                        p: 2,
                        pr: 5,
                        borderRadius: 1,
                        overflowX: 'auto',
                        fontSize: '0.75rem',
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        m: 0,
                    }}
                >
                    {code}
                </Box>
                <Tooltip title={copied ? copiedLabel : copyLabel}>
                    <IconButton
                        size="small"
                        onClick={onCopy}
                        aria-label={copyLabel}
                        sx={{
                            position: 'absolute',
                            top: 8,
                            insetInlineEnd: 8,
                            backgroundColor: 'background.paper',
                            border: '1px solid',
                            borderColor: 'divider',
                            '&:hover': { color: 'primary.dark' },
                        }}
                    >
                        <ContentCopyIcon fontSize="small" />
                    </IconButton>
                </Tooltip>
            </Box>
        </Box>
    );
}
