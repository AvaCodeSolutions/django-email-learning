import { Alert, Box, Button, DialogActions, Divider, FormControlLabel, Switch, TextField, Typography } from "@mui/material";
import RequiredTextField  from "../../../src/components/RequiredTextField.jsx";
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useState } from "react";
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';

function OrganizationForm({ successCallback, failureCallback, cancelCallback, createMode, initialName, initialDescription, initialLogoUrl, initialWebsite, initialLinkedinPage, initialYoutubeChannel, initialIsPublic, organizationId }) {
    const { localeMessages, apiBaseUrl, direction, defaultOrgSetting, defaultOrgSettings } = useAppContext();
    const defaultVisibility = defaultOrgSetting?.isPublic ?? defaultOrgSettings?.isPublic ?? true;
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
    const [isPublic, setIsPublic] = useState(initialIsPublic ?? defaultVisibility);
    const [errorMessage, setErrorMessage] = useState();

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
            setWebsiteHelperText(localeMessages["invalid_url_helper_text"]);
            valid = false;
        } else {
            setWebsiteHelperText("");
        }

        if (!validateOptionalUrl(linkedinPage)) {
            setLinkedinPageHelperText(localeMessages["invalid_url_helper_text"]);
            valid = false;
        } else {
            setLinkedinPageHelperText("");
        }

        if (!validateOptionalUrl(youtubeChannel)) {
            setYoutubeChannelHelperText(localeMessages["invalid_url_helper_text"]);
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
            is_public: isPublic,
        };

        if (logoServerPath) {
            payload.logo = logoServerPath;
        }

        if (!logoServerPath && !initialLogoUrl) {
            payload.remove_logo = true;
        }

        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/`, payload)
        .then(data => {
            successCallback(data);
        })
        .catch(error => {
            setErrorMessage(localeMessages["error_try_again"]);
            failureCallback(error instanceof apiClient.ApiError ? error.body : error);
        });
    }

    const handleCreate = () => (event) => {
        event.preventDefault();
        if (!validateForm()) {
            return;
        }

        apiClient.post(`${apiBaseUrl}/organizations/`, {
                name: name.trim(),
                description: description.trim(),
                logo: logoServerPath,
                website: website.trim(),
                linkedin_page: linkedinPage.trim(),
                youtube_channel: youtubeChannel.trim(),
                is_public: isPublic,
        })
        .then(data => {
            successCallback(data);
        })
        .catch(error => {
            setErrorMessage(localeMessages["error_try_again"]);
            failureCallback(error instanceof apiClient.ApiError ? error.body : error);
        });
    }

    return (
        <Box sx={{ p: 2 }}>
            { errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert> }
            <RequiredTextField label={localeMessages["name"]} helperText={nameHelperText} fullWidth margin="normal" value={name} onChange={(e) => setName(e.target.value)} />
            <RequiredTextField label={localeMessages["description"]} helperText={descriptionHelperText} fullWidth margin="normal" multiline rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
            <TextField label={localeMessages["website"]} type="url" fullWidth margin="normal" value={website} error={Boolean(websiteHelperText)} helperText={websiteHelperText} onChange={(e) => setWebsite(e.target.value)} />
            <TextField label={localeMessages["linkedin_page"]} type="url" fullWidth margin="normal" value={linkedinPage} error={Boolean(linkedinPageHelperText)} helperText={linkedinPageHelperText} onChange={(e) => setLinkedinPage(e.target.value)} />
            <TextField label={localeMessages["youtube_channel"]} type="url" fullWidth margin="normal" value={youtubeChannel} error={Boolean(youtubeChannelHelperText)} helperText={youtubeChannelHelperText} onChange={(e) => setYoutubeChannel(e.target.value)} />
            <Divider sx={{ my: 2 }} />
            <Box sx={{ mt: 1 }}>
                <FormControlLabel
                    control={<Switch checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} dir={direction} />}
                    label={localeMessages["organization_is_public"]}
                    sx={{ m: 0 }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {localeMessages["organization_is_public_helper_text"]}
                </Typography>
            </Box>
            <Divider sx={{ my: 2 }} />
            <ImageUpload organizationId={organizationId} initialUrl={initialLogoUrl} onUploadSuccess={(data) => {
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
