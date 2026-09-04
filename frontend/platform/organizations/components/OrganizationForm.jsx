import { Alert, Box, Button, DialogActions, Divider, FormControl, FormControlLabel, GlobalStyles, IconButton, InputAdornment, InputLabel, MenuItem, Select, Stack, Switch, TextField, Typography } from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import RequiredTextField  from "../../../src/components/RequiredTextField.jsx";
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useState, useEffect } from "react";
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import Coloris from '@melloware/coloris';
import '@melloware/coloris/dist/coloris.css';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';

const DEFAULT_BRAND_COLOR = '#4A5EC0';
const NAME_MAX_LENGTH = 60;
const DESCRIPTION_MAX_LENGTH = 1000;

const PLATFORM_OPTIONS = [
    { value: "website", labelKey: "website" },
    { value: "youtube", labelKey: "youtube_channel" },
    { value: "linkedin", labelKey: "linkedin_page" },
    { value: "facebook", labelKey: "facebook_page" },
    { value: "instagram", labelKey: "instagram" },
    { value: "tiktok", labelKey: "tiktok" },
    { value: "x", labelKey: "twitter_x" },
    { value: "whatsapp", labelKey: "whatsapp_channel" },
    { value: "telegram", labelKey: "telegram_channel" },
    { value: "substack", labelKey: "substack" },
];

function OrganizationForm({ successCallback, failureCallback, cancelCallback, createMode, initialName, initialDescription, initialLogoUrl, initialLogoPath, initialSocialLinks, initialIsPublic, initialBrandColor, organizationId, readOnly = false }) {
    const { localeMessages, apiBaseUrl: rawApiBaseUrl, direction, defaultOrgSetting, defaultOrgSettings } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const defaultVisibility = defaultOrgSetting?.isPublic ?? defaultOrgSettings?.isPublic ?? true;
    const [name, setName] = useState(initialName || "");
    const [description, setDescription] = useState(initialDescription || "");
    const [socialLinks, setSocialLinks] = useState(
        (initialSocialLinks || []).map((link) => ({ platform: link.platform, url: link.url, urlHelperText: "" }))
    );
    const [nameHelperText, setNameHelperText] = useState("");
    const [descriptionHelperText, setDescriptionHelperText] = useState("");
    const [logoServerPath, setLogoServerPath] = useState(initialLogoPath || null);
    const [isPublic, setIsPublic] = useState(initialIsPublic ?? defaultVisibility);
    const [brandColor, setBrandColor] = useState(initialBrandColor || DEFAULT_BRAND_COLOR);
    const [errorMessage, setErrorMessage] = useState();

    // Sets up the brand color picker input below. Runs once - Coloris attaches
    // itself to any current/future element matching the selector, so it
    // doesn't need to re-run when the form is remounted.
    useEffect(() => {
        Coloris.init();
        Coloris({
            el: '.coloris-input',
            // MUI's TextField already manages the input's surrounding DOM via
            // React; letting Coloris also wrap the field and inject its own
            // swatch button fights that on every re-render (breaks the
            // picker, throws off alignment). We show our own swatch instead
            // (see the InputAdornment below).
            wrap: false,
            theme: 'polaroid',
            alpha: false,
            format: 'hex',
            onChange: (color, currentEl) => {
                if (currentEl?.id === 'organization-brand-color') {
                    setBrandColor(color);
                }
            },
        });
    }, []);

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
        } else if (name.trim().length > NAME_MAX_LENGTH) {
            setNameHelperText(localeMessages["name_max_length_helper_text"]);
            valid = false;
        } else {
            setNameHelperText("");
        }

        if (!description.trim()) {
            setDescriptionHelperText(localeMessages["description_required"]);
            valid = false;
        } else if (description.length > DESCRIPTION_MAX_LENGTH) {
            setDescriptionHelperText(localeMessages["description_max_length_helper_text"]);
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
            brand_color: brandColor,
        };

        if (logoServerPath !== (initialLogoPath || null)) {
            if (logoServerPath) {
                payload.logo = logoServerPath;
            } else {
                payload.remove_logo = true;
            }
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
                brand_color: brandColor,
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
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                <ImageUpload
                    variant="avatar"
                    organizationId={organizationId}
                    initialUrl={initialLogoUrl}
                    disabled={readOnly}
                    altText={localeMessages["organization_logo_alt"]}
                    onUploadSuccess={(data) => setLogoServerPath(data.file_path)}
                    onUploadError={() => setErrorMessage(localeMessages["logo_upload_failed"])}
                />
            </Box>
            <RequiredTextField label={localeMessages["name"]} helperText={nameHelperText} fullWidth margin="normal" value={name} onChange={(e) => setName(e.target.value)} disabled={readOnly} slotProps={{ htmlInput: { maxLength: NAME_MAX_LENGTH } }} />
            <RequiredTextField
                label={localeMessages["description"]}
                helperText={descriptionHelperText || (description.length > DESCRIPTION_MAX_LENGTH
                    ? localeMessages["description_max_length_helper_text"]
                    : localeMessages["description_char_limit_helper_text"].replace("COUNT", String(description.length)))}
                fullWidth
                margin="normal"
                multiline
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={readOnly}
                slotProps={{
                    htmlInput: { maxLength: DESCRIPTION_MAX_LENGTH },
                    ...(!descriptionHelperText && description.length <= DESCRIPTION_MAX_LENGTH
                        ? { formHelperText: { sx: { color: 'text.secondary' } } }
                        : {}),
                }}
            />
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>{localeMessages["social_links"]}</Typography>
            <Stack spacing={2}>
                {socialLinks.map((link, index) => (
                    <Stack
                        key={index}
                        direction="row"
                        spacing={1}
                        sx={{ alignItems: 'flex-start', '& .MuiFormControl-root': { marginTop: '0 !important' } }}
                    >
                        <FormControl sx={{ minWidth: 160 }} size="small" disabled={readOnly}>
                            <InputLabel id={`social-link-platform-label-${index}`}>{localeMessages["social_link_platform"]}</InputLabel>
                            <Select
                                labelId={`social-link-platform-label-${index}`}
                                label={localeMessages["social_link_platform"]}
                                value={link.platform}
                                size="small"
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
                            value={link.url}
                            error={Boolean(link.urlHelperText)}
                            helperText={link.urlHelperText}
                            onChange={(e) => updateSocialLinkUrl(index, e.target.value)}
                            disabled={readOnly}
                        />
                        <IconButton aria-label={localeMessages["remove_social_link"]} onClick={() => removeSocialLink(index)} disabled={readOnly}>
                            <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Stack>
                ))}
            </Stack>
            <Button
                startIcon={<AddIcon />}
                onClick={addSocialLink}
                disabled={readOnly || socialLinks.length >= PLATFORM_OPTIONS.length}
                sx={{ mt: 1 }}
            >
                {localeMessages["add_social_link"]}
            </Button>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ mt: 1 }}>
                <FormControlLabel
                    control={<Switch checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} dir={direction} disabled={readOnly} />}
                    label={localeMessages["organization_is_public"]}
                    sx={{ m: 0 }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {localeMessages["organization_is_public_helper_text"]}
                </Typography>
            </Box>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ mt: 1 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>{localeMessages["organization_brand_color"]}</Typography>
                <TextField
                    id="organization-brand-color"
                    label={localeMessages["organization_brand_color_label"]}
                    value={brandColor}
                    onChange={(e) => setBrandColor(e.target.value)}
                    size="small"
                    disabled={readOnly}
                    slotProps={{
                        htmlInput: { className: 'coloris-input' },
                        input: {
                            startAdornment: (
                                <InputAdornment position="start">
                                    <Box sx={{ width: 18, height: 18, borderRadius: '4px', border: '1px solid', borderColor: 'divider', backgroundColor: brandColor }} />
                                </InputAdornment>
                            ),
                        },
                    }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {localeMessages["organization_brand_color_helper_text"]}
                </Typography>
            </Box>
            {/* Coloris's popup defaults to a lower z-index than MUI's Dialog
                (1300), so without this it opens invisibly behind the dialog. */}
            <GlobalStyles styles={{ '.clr-picker': { zIndex: '1400 !important' } }} />
            {!readOnly && (
                <DialogActions>
                    <Button onClick={cancelCallback}>{localeMessages["cancel"]}</Button>
                    <Button variant='contained' type="submit" color="secondary" onClick={createMode? handleCreate() : handleUpdate() }>
                        {createMode ? localeMessages["create"] : localeMessages["update"]}
                    </Button>
                </DialogActions>
            )}
        </Box>
    );
}

export default OrganizationForm;
