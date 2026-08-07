
import Base from "../../src/components/Base";
import EmptyTableState from "../../src/components/EmptyTableState.jsx";
import { Box, Button, IconButton, Grid, Dialog, Typography, TableContainer, Table, TableHead, TableRow,TableBody, TableCell, Chip, Alert } from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import render, {useAppContext} from "../../src/render";
import { useState, useEffect } from "react";
import apiClient from "../../src/apiClient.js";
import { sanitizeEndpointUrl } from '../../src/sanitizeUrl.js';


const RevokeConfirmationDialog = ({apiKey, onCancel, onSuccess}) => {

    const { localeMessages, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);

    return (
        <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
                {localeMessages["confirm_revocation"]}
            </Typography>
            <Typography>
                {localeMessages["are_you_sure_revoke_key"]}
            </Typography>
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                <Button onClick={onCancel} sx={{ mr: 1 }} variant="outlined">
                    {localeMessages["cancel"]}
                </Button>
                <Button
                    variant="contained"
                    color="error"
                    onClick={() => {
                        apiClient.del(`${apiBaseUrl}/api_keys/${apiKey.id}/`)
                        .then(() => {
                            onSuccess();
                        });
                    }}
                >
                    {localeMessages["revoke"]}
                </Button>
            </Box>
        </Box>
    );
}

/**
 * Shown once, immediately after creation. The server stores only a hash, so
 * this dialog is the only opportunity the user has to copy the token - hence
 * the warning and the deliberate lack of any "show key" affordance elsewhere.
 */
const NewApiKeyDialog = ({token, onClose}) => {
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
        <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
                {localeMessages["new_api_key_created"]}
            </Typography>
            <Alert severity="warning" sx={{ mb: 2 }}>
                {localeMessages["copy_key_now_warning"]}
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
                {copied && <Typography variant="body2" color="success.main">{localeMessages["copied"]}</Typography>}
                <Button variant="contained" onClick={onClose}>
                    {localeMessages["done"]}
                </Button>
            </Box>
        </Box>
    );
}

const statusOf = (key) => {
    if (key.revoked_at) return 'revoked';
    if (key.expires_at && new Date(key.expires_at) <= new Date()) return 'expired';
    return 'active';
}

const ApiKeys = () => {
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogContent, setDialogContent] = useState(null);
    const [apiKeyList, setApiKeyList] = useState([]);
    const [loaded, setLoaded] = useState(false);

    const { localeMessages, apiBaseUrl: rawApiBaseUrl, direction } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);

    useEffect(() => {
        if (!loaded) {
            apiClient.get(`${apiBaseUrl}/api_keys/`)
            .then(data => {
                setApiKeyList(data.api_keys);
            })
            .finally(() => {
                setLoaded(true);
            });
        }
    }, [loaded]);

    const addApiKey = () => {
        apiClient.post(`${apiBaseUrl}/api_keys/`)
        .then(data => {
            setDialogContent(<NewApiKeyDialog token={data.token} onClose={() => {
                setDialogOpen(false);
                setLoaded(false);
            }} />);
            setDialogOpen(true);
        });
    }

    const cellSx = { textAlign: direction === 'rtl' ? 'right' : 'left' };

    return (<Base breadCrumbList={[{label: localeMessages["api_keys"], href: '#'}]} showOrganizationSwitcher={false}>
        <Grid size={12} sx={{ py: 2, pl: { xs: 0, sm: 2 } }}>
        <Box sx={{ p: { xs: 1, sm: 2 }, borderRadius: { xs: 0, sm: 2 }, backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', minHeight: 300, width: { lg: '80%' } }}>
        <Typography>{localeMessages["api_key_intro"]}</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />}
                    onClick={addApiKey}
                    sx={{
                        marginLeft: direction == 'rtl' ? 2 : 0,
                        marginY: 2,
                    }}
                >
                    {localeMessages["add_api_key"]}
                </Button>
        <TableContainer sx={{ maxHeight: 440 }} >
                    <Table sx={{ tableLayout: 'fixed', width: '100%' }}>
            <TableHead>
              <TableRow>
                                <TableCell dir={direction} sx={{ width: '28%', ...cellSx }}>{localeMessages["key_id"]}</TableCell>
                                <TableCell dir={direction} sx={{ width: '14%', ...cellSx }}>{localeMessages["status"]}</TableCell>
                                <TableCell dir={direction} sx={{ width: '16%', ...cellSx }}>{localeMessages["created_by"]}</TableCell>
                                <TableCell dir={direction} sx={{ width: '16%', ...cellSx }}>{localeMessages["created_at"]}</TableCell>
                                <TableCell dir={direction} sx={{ width: '16%', ...cellSx }}>{localeMessages["last_used"]}</TableCell>
                                <TableCell sx={{ width: '10%' }}>{localeMessages["actions"]}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {apiKeyList.length === 0 && (
                <EmptyTableState
                  colSpan={6}
                  message={localeMessages['no_api_keys_found'] || 'No API keys yet.'}
                />
              )}
              { apiKeyList.map((key) => {
                const status = statusOf(key);
                return (
                <TableRow key={key.id}>
                                    <TableCell dir={direction} sx={cellSx}>
                                        <Typography
                                                component="span"
                                                sx={{ fontFamily: 'monospace', overflowWrap: 'anywhere' }}
                                        >
                                                { key.key_id }
                                        </Typography>
                                    </TableCell>
                  <TableCell dir={direction} sx={cellSx}>
                    <Chip
                      size="small"
                      label={localeMessages[status]}
                      color={status === 'active' ? 'success' : 'default'}
                      variant={status === 'active' ? 'filled' : 'outlined'}
                    />
                  </TableCell>
                  <TableCell dir={direction} sx={cellSx}>{key.created_by}</TableCell>
                  <TableCell dir={direction} sx={cellSx}>{key.created_at}</TableCell>
                  <TableCell dir={direction} sx={cellSx}>{key.last_used_at || localeMessages["never_used"]}</TableCell>
                  <TableCell>
                    {status !== 'revoked' &&
                    <IconButton
                      aria-label={localeMessages['revoke'] || 'Revoke'}
                      onClick={() => {setDialogContent(<RevokeConfirmationDialog apiKey={key} onCancel={() => setDialogOpen(false)} onSuccess={() => {
                        setLoaded(false);
                        setDialogOpen(false);
                    }} />); setDialogOpen(true);}}><DeleteIcon fontSize="small" /></IconButton>
                    }
                  </TableCell>
                </TableRow>
              )})}
            </TableBody>
          </Table>
          </TableContainer>

        </Box>
        </Grid>
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
          { dialogContent }
        </Dialog>
    </Base>)
}

export default ApiKeys;

render({children: <ApiKeys />});
