import { Alert, Box, Button, DialogActions, Divider, FormControl, FormControlLabel, IconButton, InputLabel, MenuItem, Select, Stack, Switch, TextField, Typography } from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import RequiredTextField  from "../../../src/components/RequiredTextField.jsx";
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useState } from "react";
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';

const PLATFORM_OPTIONS = [
    { value: "website", labelKey: "website" },
    { value: "youtube", labelKey: "youtube_channel" },
    { value: "linkedin", labelKey: "linkedin_page" },
];

function OrganizationForm({ successCallback, failureCallback, cancelCallback, createMode, initialName, initialDescription, initialLogoUrl, initialSocialLinks, initialIsPublic, organizationId }) {
    const { localeMessages, apiBaseUrl, direction, defaultOrgSetting, defaultOrgSettings } = useAppContext();
    const defaultVisibility = defaultOrgSetting?.isPublic ?? defaultOrgSettings?.isPublic ?? true;
    const [name, setName] = useState(initialName || "");
    const [description, setDescription] = useState(initialDescription || "");
    const [socialLinks, setSocialLinks] = useState(
        (initialSocialLinks || []).map((link) => ({ platform: link.platform, url: link.url, urlHelperText: "" }))
    );
    const [nameHelperText, setNameHelperText] = useState("");
    const [descriptionHelperText, setDescriptionHelperText] = useState("");
    const [logoServerPath, setLogoServerPath] = useState(null);
    const [isPublic, setIsPublic] = useState(initialIsPublic ?? defaultVisibility);
    const [errorMessage, setErrorMessage] = useState();

    const usedPlatforms = socialLinks.map((link) => link.platform);

    const platformOptionsFor = (currentPlatform) =>
        PLATFORM_OPTIONS.filter((option) => option.value === currentPlatform || !usedPlatforms.includes(option.value));

    const addSocialLink = () => {
        const nextPlatform = PLATFORM_OPTIONS.find((option) => !usedPlatforms.includes(option.value));
        if (!nextPlatform) {
            return;
        }
        setSocialLinks((prev) => [...prev, { platform: nextPlatform.value, url: "", urlHelperText: "" }]);
    };

    const removeSocialLink = (index) => {
        setSocialLinks((prev) => prev.filter((_, i) => i !== index));
    };

    const updateSocialLinkPlatform = (index, platform) => {
        setSocialLinks((prev) => prev.map((link, i) => (i === index ? { ...link, platform } : link)));
    };

    const updateSocialLinkUrl = (index, url) => {
        setSocialLinks((prev) => prev.map((link, i) => (i === index ? { ...link, url, urlHelperText: "" } : link)));
    };

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

        setSocialLinks((prev) =>
            prev.map((link) => {
                if (!link.url.trim() || !validateOptionalUrl(link.url)) {
                    valid = false;
                    return { ...link, urlHelperText: localeMessages["invalid_url_helper_text"] };
                }
                return { ...link, urlHelperText: "" };
            })
        );

        return valid;
    }

    const buildSocialLinksPayload = () =>
        socialLinks.map(({ platform, url }) => ({ platform, url: url.trim() }));

    const handleUpdate = () => (event) => {
        event.preventDefault();
        if (!validateForm()) {
            return;
        }

        let payload = {
            name: name.trim(),
            description: description.trim(),
            social_links: buildSocialLinksPayload(),
            is_public: isPublic,
        };

        if (logoServerPath) {
            payload.logo = logoServerPath;
        }

        if (!logoServerPath && initialLogoUrl) {
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
                social_links: buildSocialLinksPayload(),
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
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>{localeMessages["social_links"]}</Typography>
            <Stack spacing={2}>
                {socialLinks.map((link, index) => (
                    <Stack key={index} direction="row" spacing={1} sx={{ alignItems: 'flex-start' }}>
                        <FormControl sx={{ minWidth: 160 }} margin="normal">
                            <InputLabel id={`social-link-platform-label-${index}`}>{localeMessages["social_link_platform"]}</InputLabel>
                            <Select
                                labelId={`social-link-platform-label-${index}`}
                                label={localeMessages["social_link_platform"]}
                                value={link.platform}
                                onChange={(e) => updateSocialLinkPlatform(index, e.target.value)}
                            >
                                {platformOptionsFor(link.platform).map((option) => (
                                    <MenuItem key={option.value} value={option.value}>{localeMessages[option.labelKey]}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <TextField
                            label={localeMessages["social_link_url"]}
                            type="url"
                            fullWidth
                            margin="normal"
                            value={link.url}
                            error={Boolean(link.urlHelperText)}
                            helperText={link.urlHelperText}
                            onChange={(e) => updateSocialLinkUrl(index, e.target.value)}
                        />
                        <IconButton aria-label={localeMessages["remove_social_link"]} onClick={() => removeSocialLink(index)} sx={{ mt: 2 }}>
                            <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Stack>
                ))}
            </Stack>
            <Button
                startIcon={<AddIcon />}
                onClick={addSocialLink}
                disabled={socialLinks.length >= PLATFORM_OPTIONS.length}
                sx={{ mt: 1 }}
            >
                {localeMessages["add_social_link"]}
            </Button>
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
