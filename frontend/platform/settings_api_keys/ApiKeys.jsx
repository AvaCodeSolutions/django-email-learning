
import Base from "../../src/components/Base";
import EmptyTableState from "../../src/components/EmptyTableState.jsx";
import { Box, Button, IconButton, Grid, Dialog, Typography, TableContainer, Table, TableHead, TableRow,TableBody, TableCell } from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import render, {useAppContext} from "../../src/render";
import { useState, useEffect } from "react";
import apiClient from "../../src/apiClient.js";
import { sanitizeEndpointUrl } from '../../src/sanitizeUrl.js';



const DeleteConfirmationDialog = ({apiKey, onCancel, onSuccess}) => {

    const { localeMessages, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);

    return (
        <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
                {localeMessages["confirm_deletion"]}
            </Typography>
            <Typography>
                {localeMessages["are_you_sure_delete_key"]}
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
                    {localeMessages["delete"]}
                </Button>
            </Box>
        </Box>
    );
}

const ApiKeys = () => {
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogContent, setDialogContent] = useState(null);
    const [apiKeyList, setApiKeyList] = useState([]);
    const [loaded, setLoaded] = useState(false);

    const { localeMessages, apiBaseUrl: rawApiBaseUrl, direction } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);

    useEffect(() => {
        // Fetch API keys from the backend
        if (!loaded) {
        apiClient.get(`${apiBaseUrl}/api_keys/`)
        .then(data => {
            setApiKeyList(data.api_keys.map((key) => ({
                id: key.id,
                key: key.key,
                created_by: key.created_by,
                created_at: key.created_at,
                visible: false,
            })));
        })
        .finally(() => {
            setLoaded(true);
        });
    }
    }, [loaded]);

    const addApiKey = () => {
        apiClient.post(`${apiBaseUrl}/api_keys/`)
        .then(data => {
            data.visible = false;
            setApiKeyList([...apiKeyList, data]);
        });
    }

    const copyApiKey = async (apiKeyValue) => {
        try {
            await navigator.clipboard.writeText(apiKeyValue);
        } catch (error) {
            console.error('Failed to copy API key:', error);
        }
    }

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
                                <TableCell dir={direction} sx={{ width: '50%', textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["key"]}</TableCell>
                                <TableCell dir={direction} sx={{ width: '20%', textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["created_by"]}</TableCell>
                                <TableCell dir={direction} sx={{ width: '20%', textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["created_at"]}</TableCell>
                                <TableCell sx={{ width: '10%' }}>{localeMessages["actions"]}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {apiKeyList.length === 0 && (
                <EmptyTableState
                  colSpan={4}
                  message={localeMessages['no_api_keys_found'] || 'No API keys yet.'}
                />
              )}
              { apiKeyList.map((key) => (
                <TableRow key={key.id}>
                                    <TableCell dir={direction} sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
                                                <Typography
                                                        component="span"
                                                        sx={{
                                                                fontFamily: 'monospace',
                                                                overflowWrap: 'anywhere',
                                                                whiteSpace: 'normal',
                                                                flex: 1,
                                                        }}
                                                >
                                                        { key.visible ? key.key : '••••••••••••••••' }
                                                </Typography>
                                                <IconButton
                                                        size="small"
                                                        onClick={() => copyApiKey(key.key)}
                                                        aria-label={localeMessages['copy'] || 'Copy'}
                                                >
                                                        <ContentCopyIcon fontSize="small" />
                                                </IconButton>
                                        </Box>
                                    </TableCell>
                  <TableCell dir={direction} sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{key.created_by}</TableCell>
                  <TableCell dir={direction} sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{key.created_at}</TableCell>
                  <TableCell>
                    <IconButton onClick={() => {setDialogContent(<DeleteConfirmationDialog apiKey={key} onCancel={() => setDialogOpen(false)} onSuccess={() => {
                        setLoaded(false);
                        setDialogOpen(false);
                    }} />); setDialogOpen(true);}}><DeleteIcon fontSize="small" /></IconButton>
                    {key.visible ?
                    <IconButton onClick={() => {
                        setApiKeyList(apiKeyList.map((k) => {
                            if (k.id === key.id) {
                                return {...k, visible: false};
                            }
                            return k;
                        }));
                    }}><VisibilityIcon fontSize="small" /></IconButton> :
                    <IconButton onClick={() => {
                        setApiKeyList(apiKeyList.map((k) => {
                            if (k.id === key.id) {
                                return {...k, visible: true};
                            }
                            return k;
                        }));
                    }}><VisibilityOffIcon fontSize="small" /></IconButton>
                    }
                  </TableCell>
                </TableRow>
              ))}
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
