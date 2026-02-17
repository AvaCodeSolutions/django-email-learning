import { Alert, Box, Button, DialogActions } from "@mui/material";
import RequiredTextField  from "../../../src/components/RequiredTextField.jsx";
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useState } from "react";
import { getCookie } from '../../../src/utils.js';
import { useAppContext } from '../../../src/render.jsx';

function OrganizationForm({ successCallback, failureCallback, cancelCallback, createMode, initialName, initialDescription, initialLogoUrl, organizationId }) {
    const [name, setName] = useState(initialName || "");
    const [description, setDescription] = useState(initialDescription || "");
    const [nameHelperText, setNameHelperText] = useState("");
    const [descriptionHelperText, setDescriptionHelperText] = useState("");
    const [logoServerPath, setLogoServerPath] = useState(null);
    const [errorMessage, setErrorMessage] = useState();
    const { localeMessages, apiBaseUrl } = useAppContext();

    const validateForm = () => {
        let valid = true;
        if (!name.trim()) {
            setNameHelperText(localeMessages["name_required"]);
            valid = false;
        } else {
            setNameHelperText("");
        }

        if (!description.trim()) {
            setDescriptionHelperText(localeMessages["description_required"]);
            valid = false;
        } else {
            setDescriptionHelperText("");
        }

        return valid;
    }

    const handleUpdate = () => (event) => {
        event.preventDefault();
        if (!validateForm()) {
            return;
        }

        let payload = {
            name: name,
            description: description,
        };

        if (logoServerPath) {
            payload.logo = logoServerPath;
        }

        if (!logoServerPath && !initialLogoUrl) {
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
            setErrorMessage(localeMessages["error_try_again"]);
            failureCallback(error);
        });
    }

    const handleCreate = () => (event) => {
        event.preventDefault();
        if (!validateForm()) {
            return;
        }

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
            setErrorMessages(localeMessages["error_try_again"]);
        });
    }

    return (
        <Box p={2}>
            { errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert> }
            <RequiredTextField label={localeMessages["name"]} helperText={nameHelperText} fullWidth margin="normal" value={name} onChange={(e) => setName(e.target.value)} />
            <RequiredTextField label={localeMessages["description"]} helperText={descriptionHelperText} fullWidth margin="normal" multiline rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
            <ImageUpload initialUrl={initialLogoUrl} onUploadSuccess={(data) => {
                setLogoServerPath(data.file_path);
            }} onUploadError={(error) => {
                setErrorMessages(localeMessages["logo_upload_failed"]);
            }} />
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
