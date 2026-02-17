
import Base from "../../src/components/Base";
import { Box, Button, IconButton, Grid, Dialog, Typography, TableContainer, Table, TableHead, TableRow,TableBody, TableCell } from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import render, {useAppContext} from "../../src/render";
import { useState, useEffect } from "react";
import { getCookie } from "../../src/utils.js";



const DeleteConfirmationDialog = ({apiKey, onCancel, onSuccess}) => {

    const { localeMessages, apiBaseUrl } = useAppContext();

    return (
        <Box p={2}>
            <Typography variant="h6" gutterBottom>
                {localeMessages["confirm_deletion"]}
            </Typography>
            <Typography>
                {localeMessages["are_you_sure_delete_key"]}
            </Typography>
            <Box mt={2} display="flex" justifyContent="flex-end">
                <Button onClick={onCancel} sx={{ mr: 1 }} variant="outlined">
                    {localeMessages["cancel"]}
                </Button>
                <Button
                    variant="contained"
                    color="error"
                    onClick={() => {
                        fetch(`${apiBaseUrl}/api_keys/${apiKey.id}/`, {
                            method: 'DELETE',
                            headers: {
                                'X-CSRFToken': getCookie('csrftoken'),
                            },
                        })
                        .then(response => {
                            if (response.ok) {
                                onSuccess();
                            }
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

    const { localeMessages, apiBaseUrl, direction } = useAppContext();

    useEffect(() => {
        // Fetch API keys from the backend
        if (!loaded) {
        fetch(`${apiBaseUrl}/api_keys/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
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
        fetch(`${apiBaseUrl}/api_keys/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
        .then(data => {
            data.visible = false;
            setApiKeyList([...apiKeyList, data]);
        });
    }

    return (<Base breadCrumbList={[{label: localeMessages["api_keys"], href: '#'}]} showOrganizationSwitcher={false}>
        <Grid size={12} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, backgroundColor: 'background.paper', minHeight: 300, width: { lg: '80%' } }}>
        <Typography>{localeMessages["api_key_intro"]}</Typography>
        <Button variant="contained" startIcon={<AddIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />} onClick={addApiKey} sx={{ marginLeft: direction == 'rtl' ? 2 : 0, marginY: 2 }}>{localeMessages["add_api_key"]}</Button>
        { apiKeyList.length > 0 && (<TableContainer sx={{ maxHeight: 440, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }} >
          <Table>
            <TableHead>
              <TableRow>
                <TableCell dir={direction} sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["key"]}</TableCell>
                <TableCell dir={direction} sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["created_by"]}</TableCell>
                <TableCell dir={direction} sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["created_at"]}</TableCell>
                <TableCell sx={{ width: '100px' }}>{localeMessages["actions"]}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              { apiKeyList.map((key) => (
                <TableRow key={key.id}>
                  <TableCell dir={direction} sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{ key.visible ? key.key : '••••••••••••••••' }</TableCell>
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

        )}
        </Box>
        </Grid>
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
          { dialogContent }
        </Dialog>
    </Base>)
}

render({children: <ApiKeys />});
