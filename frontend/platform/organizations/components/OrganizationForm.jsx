import { Alert, Box, Button, DialogActions, TextField } from "@mui/material";
import RequiredTextField  from "../../../src/components/RequiredTextField.jsx";
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useState } from "react";
import { getCookie } from '../../../src/utils.js';
import { useAppContext } from '../../../src/render.jsx';

function OrganizationForm({ successCallback, failureCallback, cancelCallback, createMode, initialName, initialDescription, initialLogoUrl, initialWebsite, initialLinkedinPage, initialYoutubeChannel, organizationId }) {
    const [name, setName] = useState(initialName || "");
    const [description, setDescription] = useState(initialDescription || "");
    const [website, setWebsite] = useState(initialWebsite || "");
    const [linkedinPage, setLinkedinPage] = useState(initialLinkedinPage || "");
    const [youtubeChannel, setYoutubeChannel] = useState(initialYoutubeChannel || "");
    const [nameHelperText, setNameHelperText] = useState("");
    const [descriptionHelperText, setDescriptionHelperText] = useState("");
    const [websiteHelperText, setWebsiteHelperText] = useState("");
    const [linkedinPageHelperText, setLinkedinPageHelperText] = useState("");
    const [youtubeChannelHelperText, setYoutubeChannelHelperText] = useState("");
    const [logoServerPath, setLogoServerPath] = useState(null);
    const [errorMessage, setErrorMessage] = useState();
    const { localeMessages, apiBaseUrl } = useAppContext();

    const validateOptionalUrl = (value) => {
        const trimmedValue = value.trim();

        if (!trimmedValue) {
            return true;
        }

        try {
            const parsedUrl = new URL(trimmedValue);

            return ["http:", "https:"].includes(parsedUrl.protocol) && Boolean(parsedUrl.hostname);
        } catch {
            return false;
        }
    };

    const validateForm = () => {
        let valid = true;
        setErrorMessage(undefined);

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

        if (!validateOptionalUrl(website)) {
            setWebsiteHelperText("Enter a valid URL starting with http:// or https://");
            valid = false;
        } else {
            setWebsiteHelperText("");
        }

        if (!validateOptionalUrl(linkedinPage)) {
            setLinkedinPageHelperText("Enter a valid URL starting with http:// or https://");
            valid = false;
        } else {
            setLinkedinPageHelperText("");
        }

        if (!validateOptionalUrl(youtubeChannel)) {
            setYoutubeChannelHelperText("Enter a valid URL starting with http:// or https://");
            valid = false;
        } else {
            setYoutubeChannelHelperText("");
        }

        return valid;
    }

    const handleUpdate = () => (event) => {
        event.preventDefault();
        if (!validateForm()) {
            return;
        }

        let payload = {
            name: name.trim(),
            description: description.trim(),
            website: website.trim(),
            linkedin_page: linkedinPage.trim(),
            youtube_channel: youtubeChannel.trim(),
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
                name: name.trim(),
                description: description.trim(),
                logo: logoServerPath,
                website: website.trim(),
                linkedin_page: linkedinPage.trim(),
                youtube_channel: youtubeChannel.trim(),
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
            setErrorMessage(localeMessages["error_try_again"]);
            failureCallback(error);
        });
    }

    return (
        <Box p={2}>
            { errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert> }
            <RequiredTextField label={localeMessages["name"]} helperText={nameHelperText} fullWidth margin="normal" value={name} onChange={(e) => setName(e.target.value)} />
            <RequiredTextField label={localeMessages["description"]} helperText={descriptionHelperText} fullWidth margin="normal" multiline rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
            <TextField label="Website" type="url" fullWidth margin="normal" value={website} error={Boolean(websiteHelperText)} helperText={websiteHelperText} onChange={(e) => setWebsite(e.target.value)} />
            <TextField label="LinkedIn page" type="url" fullWidth margin="normal" value={linkedinPage} error={Boolean(linkedinPageHelperText)} helperText={linkedinPageHelperText} onChange={(e) => setLinkedinPage(e.target.value)} />
            <TextField label="YouTube channel" type="url" fullWidth margin="normal" value={youtubeChannel} error={Boolean(youtubeChannelHelperText)} helperText={youtubeChannelHelperText} onChange={(e) => setYoutubeChannel(e.target.value)} />
            <ImageUpload initialUrl={initialLogoUrl} onUploadSuccess={(data) => {
                setLogoServerPath(data.file_path);
            }} onUploadError={(error) => {
                setErrorMessage(localeMessages["logo_upload_failed"]);
            }} />
            <DialogActions>
                <Button onClick={cancelCallback}>{localeMessages["cancel"]}</Button>
                <Button variant='contained' type="submit" color="secondary" onClick={createMode? handleCreate() : handleUpdate() }>
                    {createMode ? localeMessages["create"] : localeMessages["update"]}
                </Button>
            </DialogActions>
        </Box>
    );
}

export default OrganizationForm;
