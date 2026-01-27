import { styled } from '@mui/material/styles';
import { Box, Button, DialogActions } from "@mui/material";
import RequiredTextField  from "../../../src/components/RequiredTextField.jsx";
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { useState, useEffect, use } from "react";
import { getCookie } from '../../../src/utils.js';

function OrganizationForm({ successCallback, failureCallback, cancelCallback, createMode, initialName, initialDescription, initialLogoUrl, organizationId }) {
    const [name, setName] = useState(initialName || "");
    const [description, setDescription] = useState(initialDescription || "");
    const [nameHelperText, setNameHelperText] = useState("");
    const [descriptionHelperText, setDescriptionHelperText] = useState("");
    const [logoFile, setLogoFile] = useState(null);
    const [logoUrl, setLogoUrl] = useState(initialLogoUrl || null);
    const [logoServerPath, setLogoServerPath] = useState(null);

    const apiBaseUrl = localStorage.getItem('apiBaseUrl');

    const removeLogo = () => {
        setLogoUrl(null);
        setLogoServerPath(null);
        setLogoFile(null);
    }

    const handleUpdate = () => (event) => {
        event.preventDefault();

        let payload = {
            name: name,
            description: description,
        };

        if (logoServerPath) {
            payload.logo = logoServerPath;
        }

        if (!logoServerPath && !logoUrl) {
            payload.remove_logo = true;
        }

        fetch(`${apiBaseUrl}/organizations/${organizationId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(payload),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw data;
                });
            }
            return response.json();
        })
        .then(data => {
            successCallback(data);
        })
        .catch(error => {
            failureCallback(error);
        });
    }

    const handleCreate = () => (event) => {
        event.preventDefault();
        fetch(`${apiBaseUrl}/organizations/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                name: name,
                description: description,
                logo: logoServerPath,
            }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw data;
                });
            }
            return response.json();
        })
        .then(data => {
            successCallback(data);
        })
        .catch(error => {
            failureCallback(error);
        });
    }

    useEffect(() => {
        if (logoFile) {
            fetch(`${apiBaseUrl}/organizations/1/file/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: (() => {
                    const formData = new FormData();
                    formData.append('file', logoFile);
                    return formData;
                })(),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('File upload failed');
                }
                return response.json();
            })
            .then(data => {
                console.log('File uploaded successfully:', data);
                setLogoUrl(data.file_url);
                setLogoServerPath(data.file_path);
                console.log('File path set to:', logoServerPath);
            })
            .catch(error => {
                console.error('Error uploading file:', error);
            });
        }
    }, [logoFile]);

    const VisuallyHiddenInput = styled('input')({
        clip: 'rect(0 0 0 0)',
        clipPath: 'inset(50%)',
        height: 1,
        overflow: 'hidden',
        position: 'absolute',
        bottom: 0,
        left: 0,
        whiteSpace: 'nowrap',
        width: 1,
    });

    return (
        <Box p={2}>
            <RequiredTextField label={localeMessages["name"]} helperText={nameHelperText} fullWidth margin="normal" value={name} onChange={(e) => setName(e.target.value)} />
            <RequiredTextField label={localeMessages["description"]} helperText={descriptionHelperText} fullWidth margin="normal" multiline rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
            { !logoUrl ? <Button
            component="label"
            role={undefined}
            variant="contained"
            tabIndex={-1}
            startIcon={<CloudUploadIcon sx={{ marginLeft: direction === 'rtl' ? 1 : 0 }} />}
            sx={{ textAlign: direction === 'rtl' ? 'right' : 'left', mt: 2, mb: 2}}
            dir={direction}
            >
            {localeMessages["logo"]}
            <VisuallyHiddenInput
                type="file"
                onChange={(event) => setLogoFile(event.target.files[0])}
            />
            </Button>
            : (<><img src={logoUrl} alt={localeMessages["organization_logo"]} style={{ marginTop: '10px', maxHeight: '100px' }} /><br />
                <Button variant="text" color="secondary" onClick={removeLogo}>{localeMessages["remove_logo"]}</Button></>
            )}
            <DialogActions>
                <Button onClick={cancelCallback}>{localeMessages["cancel"]}</Button>
                <Button variant='contained' type="submit" color="primary" onClick={createMode? handleCreate() : handleUpdate() }>
                    {createMode ? localeMessages["create"] : localeMessages["update"]}
                </Button>
            </DialogActions>
        </Box>
    );
}

export default OrganizationForm;
