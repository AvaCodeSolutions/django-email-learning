import { Alert, Box, Button, Divider, IconButton, MenuItem, Stack, TextField, Tooltip, FormControlLabel, Switch, Typography, LinearProgress } from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import RequiredTextField  from '../../../src/components/RequiredTextField.jsx';
import AddImapConnectionForm from '../components/AddImapConnectionForm.jsx';
import AddNewsletterForm from '../components/AddNewsletterForm.jsx';
import AddInstructorsSection from '../components/AddInstructorsSection.jsx';
import { useAppContext } from '../../../src/render.jsx';
import ImageUpload from '../../../src/components/ImageUpload.jsx';
import { useEffect, useState } from 'react';
import apiClient from '../../../src/apiClient.js';

const MAX_EXTERNAL_REFERENCES = 10;

const createEmptyExternalReference = () => ({ name: '', url: '' });

const normalizeExternalReferences = (references = []) => references
    .map((reference) => ({
        name: (reference?.name || '').trim(),
        url: (reference?.url || '').trim(),
    }))
    .filter((reference) => reference.name || reference.url);

const externalReferencesChanged = (originalReferences, currentReferences) => {
    if (originalReferences.length !== currentReferences.length) {
        return true;
    }

    return originalReferences.some((reference, index) => (
        reference.name !== currentReferences[index]?.name
        || reference.url !== currentReferences[index]?.url
    ));
};

function CourseForm({successCallback, failureCallback, cancelCallback, activeOrganizationId, createMode, courseId}) {
    const { localeMessages, apiBaseUrl, direction, languageOptions = [], availableFeatures = [], organizationIsPublic } = useAppContext();
    const newslettersEnabled = availableFeatures.includes('newsletters');
    const createNewsletterEnabled = availableFeatures.includes('create_newsletter');
    const [courseTitle, setCourseTitle] = useState("")
    const [courseSlug, setCourseSlug] = useState("")
    const [courseDescription, setCourseDescription] = useState("")
    const [courseTargetAudience, setCourseTargetAudience] = useState("")
    const [courseLanguage, setCourseLanguage] = useState("")
    const [isPublic, setIsPublic] = useState(createMode && organizationIsPublic)
    const [sendCertificate, setSendCertificate] = useState(true)
    const [addImapConnection, setAddImapConnection] = useState(false)
    const [imapConnectionId, setImapConnectionId] = useState(null)
    const [addNewsletter, setAddNewsletter] = useState(false)
    const [newsletterId, setNewsletterId] = useState(null)
    const [addInstructors, setAddInstructors] = useState(false)
    const [selectedInstructorIds, setSelectedInstructorIds] = useState([])
    const [titleHelperText, setTitleHelperText] = useState("")
    const [slugHelperText, setSlugHelperText] = useState("")
    const [descriptionHelperText, setDescriptionHelperText] = useState("")
    const [languageHelperText, setLanguageHelperText] = useState("")
    const [externalReferenceErrors, setExternalReferenceErrors] = useState([])
    const [errorMessage, setErrorMessage] = useState("")
    const [imageUrl, setImageUrl] = useState(null)
    const [imageServerPath, setImageServerPath] = useState(null)
    const [externalReferences, setExternalReferences] = useState([])
    const [originalExternalReferences, setOriginalExternalReferences] = useState([])
    const [initialValues, setInitialValues] = useState({
        title: "",
        description: "",
        targetAudience: "",
        language: "",
        isPublic: true,
        sendCertificate: true,
        imapConnectionId: null,
        newsletterId: null,
        imageServerPath: null,
        instructors: [],
    })

    const switchImapConnection = () => {
        if (addImapConnection) {
            setAddImapConnection(false)
        } else {
            setAddImapConnection(true)
        }
    }

    useEffect(() => {
        if (createMode && !courseLanguage && languageOptions.length > 0) {
            setCourseLanguage("en"); // Default to English or you can choose the first language in the options
        }
    }, [createMode, courseLanguage, languageOptions]);

    useEffect(() => {
        if (!organizationIsPublic) {
            setIsPublic(false);
        }
    }, [organizationIsPublic]);

    useEffect(() => {
        if (!createMode && courseId) {
            apiClient.get(apiBaseUrl + '/organizations/' + activeOrganizationId + '/courses/' + courseId + '/')
            .then(data => {
                setCourseTitle(data.title);
                setCourseSlug(data.slug);
                setCourseDescription(data.description);
                setCourseTargetAudience(data.target_audience || "");
                setCourseLanguage(data.language || "");
                setIsPublic(organizationIsPublic ? (data.is_public ?? true) : false);
                setSendCertificate(data.send_certificate ?? true);
                setImageUrl(data.image);
                setImageServerPath(data.image_path);
                setInitialValues({
                    title: data.title || "",
                    description: data.description || "",
                    targetAudience: data.target_audience || "",
                    language: data.language || "",
                    isPublic: data.is_public ?? true,
                    sendCertificate: data.send_certificate ?? true,
                    imapConnectionId: data.imap_connection_id ?? null,
                    newsletterId: data.newsletter_id ?? null,
                    imageServerPath: data.image_path ?? null,
                    instructors: (data.instructors || []).map((i) => i.id),
                });
                const initialExternalReferences = (data.external_references || []).map((reference) => ({
                    name: reference.name || '',
                    url: reference.url || '',
                }));
                setExternalReferences(initialExternalReferences);
                setOriginalExternalReferences(normalizeExternalReferences(initialExternalReferences));
                if (data.imap_connection_id) {
                    setImapConnectionId(data.imap_connection_id);
                    setAddImapConnection(true);
                }
                if (data.newsletter_id) {
                    setNewsletterId(data.newsletter_id);
                    setAddNewsletter(true);
                }
                const initialInstructors = (data.instructors || []).map((i) => i.id);
                setSelectedInstructorIds(initialInstructors);
                if (initialInstructors.length > 0) {
                    setAddInstructors(true);
                }
            })
            .catch((error) => {
                console.error('Error:', error);
                if (error)
                failureCallback(error);
            });
        }
    }, [createMode, courseId]);

    const validateForm = () => {
        let isValid = true
        const noWhitespacePattern = /^\S+$/;
        const nextExternalReferenceErrors = externalReferences.map((reference) => {
            const name = reference.name.trim();
            const url = reference.url.trim();
            const rowErrors = { name: false, url: false };

            if (!name && !url) {
                return rowErrors;
            }

            if (!name) {
                rowErrors.name = true;
                isValid = false;
            }

            if (!url) {
                rowErrors.url = true;
                isValid = false;
                return rowErrors;
            }

            try {
                new URL(url);
            } catch {
                rowErrors.url = true;
                isValid = false;
            }

            return rowErrors;
        });

        if (!courseTitle) {
            setTitleHelperText(localeMessages["title_required_helper_text"]);
            isValid = false;
        } else {
            setTitleHelperText("");
        }
        if (!courseSlug) {
            setSlugHelperText(localeMessages["slug_required_helper_text"]);
            isValid = false;
        } else if (!noWhitespacePattern.test(courseSlug)) {
            setSlugHelperText(localeMessages["slug_no_space"]);
            isValid = false;
        } else {
            setSlugHelperText("");
        }
        if (!courseDescription) {
            setDescriptionHelperText(localeMessages["description_required_helper_text"]);
            isValid = false;
        } else {
            setDescriptionHelperText("");
        }
        if (!courseLanguage) {
            setLanguageHelperText(localeMessages["language_required_helper_text"]);
            isValid = false;
        } else {
            setLanguageHelperText("");
        }

        setExternalReferenceErrors(nextExternalReferenceErrors);

        return isValid;
    }

    const handleExternalReferenceChange = (index, field, value) => {
        setExternalReferences((currentReferences) => currentReferences.map((reference, currentIndex) => (
            currentIndex === index ? { ...reference, [field]: value } : reference
        )));
        setExternalReferenceErrors((currentErrors) => currentErrors.map((error, currentIndex) => (
            currentIndex === index ? { ...error, [field]: false } : error
        )));
    }

    const handleAddExternalReference = () => {
        if (externalReferences.length >= MAX_EXTERNAL_REFERENCES) {
            return;
        }
        setExternalReferences((currentReferences) => [...currentReferences, createEmptyExternalReference()]);
        setExternalReferenceErrors((currentErrors) => [...currentErrors, { name: false, url: false }]);
    }

    const handleRemoveExternalReference = (indexToRemove) => {
        setExternalReferences((currentReferences) => currentReferences.filter((_, index) => index !== indexToRemove));
        setExternalReferenceErrors((currentErrors) => currentErrors.filter((_, index) => index !== indexToRemove));
    }

    const handleUpdateCourse = () => {
        const isValid = validateForm()
        if (!isValid) {
            return
        }
        const normalizedExternalReferences = normalizeExternalReferences(externalReferences);
        const trimmedTargetAudience = courseTargetAudience.trim();
        const currentImapConnectionId = addImapConnection && imapConnectionId != null
            ? parseInt(imapConnectionId)
            : null;
        const currentNewsletterId = addNewsletter && newsletterId != null
            ? parseInt(newsletterId)
            : null;
        const updatePayload = {
            image: imageServerPath === initialValues.imageServerPath
                ? 'SKIP'
                : (imageServerPath ? imageServerPath : null)
        };

        if (courseTitle !== initialValues.title) {
            updatePayload.title = courseTitle;
        }

        if (courseDescription !== initialValues.description) {
            updatePayload.description = courseDescription;
        }

        if (trimmedTargetAudience !== initialValues.targetAudience.trim()) {
            updatePayload.target_audience = trimmedTargetAudience;
        }

        if (courseLanguage !== initialValues.language) {
            updatePayload.language = courseLanguage;
        }

        if (isPublic !== initialValues.isPublic) {
            updatePayload.is_public = isPublic;
        }

        if (sendCertificate !== initialValues.sendCertificate) {
            updatePayload.send_certificate = sendCertificate;
        }

        if (currentImapConnectionId !== initialValues.imapConnectionId) {
            if (currentImapConnectionId == null) {
                updatePayload.reset_imap_connection = true;
            } else {
                updatePayload.imap_connection_id = currentImapConnectionId;
            }
        }

        if (currentNewsletterId !== initialValues.newsletterId) {
            if (currentNewsletterId == null) {
                updatePayload.reset_newsletter = true;
            } else {
                updatePayload.newsletter_id = currentNewsletterId;
            }
        }

        if (externalReferencesChanged(originalExternalReferences, normalizedExternalReferences)) {
            updatePayload.external_references = normalizedExternalReferences;
        }

        const currentInstructors = addInstructors ? selectedInstructorIds : [];
        const sortedCurrent = [...currentInstructors].sort((a, b) => a - b);
        const sortedInitial = [...(initialValues.instructors || [])].sort((a, b) => a - b);
        if (JSON.stringify(sortedCurrent) !== JSON.stringify(sortedInitial)) {
            updatePayload.instructors = currentInstructors;
        }

        apiClient.post(apiBaseUrl + '/organizations/' + activeOrganizationId + '/courses/' + courseId + '/', updatePayload)
        .then(data => {
            if (data.error) {
                setErrorMessage(data.error);
                failureCallback(data);
            } else {
                setInitialValues({
                    title: data.title || courseTitle,
                    description: data.description || courseDescription,
                    targetAudience: data.target_audience || trimmedTargetAudience,
                    language: data.language || courseLanguage,
                    isPublic: data.is_public ?? isPublic,
                    sendCertificate: data.send_certificate ?? sendCertificate,
                    imapConnectionId: data.imap_connection_id ?? currentImapConnectionId,
                    newsletterId: data.newsletter_id ?? currentNewsletterId,
                    imageServerPath: data.image_path ?? imageServerPath,
                });
                setOriginalExternalReferences(normalizeExternalReferences(data.external_references || normalizedExternalReferences));
                console.log('Success:', data);
                successCallback(data);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            if (error instanceof apiClient.ApiError && error.status === 409 && error.body?.error) {
                setErrorMessage(error.body.error);
                failureCallback(error.body);
            } else {
                if (error instanceof apiClient.ApiError && error.status >= 500) {
                    setErrorMessage(localeMessages["server_error"]);
                }
                failureCallback(error);
            }
        });
    };

    const handleCreateCourse = () => {
        const isValid = validateForm()
        if (!isValid) {
            return
        }
        const normalizedExternalReferences = normalizeExternalReferences(externalReferences);
        apiClient.post(apiBaseUrl + '/organizations/' + activeOrganizationId + '/courses/', {
            title: courseTitle,
            slug: courseSlug,
            description: courseDescription,
            target_audience: courseTargetAudience.trim(),
            language: courseLanguage,
            is_public: isPublic,
            send_certificate: sendCertificate,
            imap_connection_id: imapConnectionId ? parseInt(imapConnectionId) : null,
            newsletter_id: addNewsletter && newsletterId ? parseInt(newsletterId) : null,
            external_references: normalizedExternalReferences.length > 0 ? normalizedExternalReferences : null,
            image: imageServerPath ? imageServerPath : null,
            instructors: addInstructors && selectedInstructorIds.length > 0 ? selectedInstructorIds : null,
        })
        .then(data => {
            if (data.error) {
                setErrorMessage(data.error);
                failureCallback(data);
            } else {
                console.log('Success:', data);
                // Optionally reset form fields here
                setCourseTitle("");
                setCourseSlug("");
                setCourseDescription("");
                setCourseTargetAudience("");
                setCourseLanguage(languageOptions.length > 0 ? languageOptions[0].value : "");
                setIsPublic(true);
                setSendCertificate(true);
                setExternalReferences([]);
                setOriginalExternalReferences([]);
                setExternalReferenceErrors([]);
                successCallback(data);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            if (error instanceof apiClient.ApiError && error.status === 409 && error.body?.error) {
                setErrorMessage(error.body.error);
                failureCallback(error.body);
            } else {
                if (error instanceof apiClient.ApiError && error.status >= 500) {
                    setErrorMessage(localeMessages["server_error"]);
                }
                failureCallback(error);
            }
        });
    };

    return (<Box sx={{ p: 2 }}>
              { (!createMode && courseTitle=="") ? <LinearProgress /> : <>
              { errorMessage && <Alert severity="error" sx={{ marginBottom: "10px" }}>{errorMessage}</Alert> }
              <RequiredTextField label={localeMessages["course_title"]} helperText={titleHelperText} fullWidth margin="normal" value={courseTitle} onChange={(e) => setCourseTitle(e.target.value)} />
              <Tooltip title={createMode ? localeMessages["slug_tooltip"] : ""}>
                                <RequiredTextField label={localeMessages["course_slug"]} helperText={slugHelperText} fullWidth margin="normal" value={courseSlug} onChange={(e) => setCourseSlug(e.target.value)} slotProps={{ htmlInput: { pattern: '^\\S+$', title: localeMessages['slug_no_space'] } }} {...(!createMode ? { disabled: true } : {})} />
              </Tooltip>
                            <RequiredTextField
                                label={localeMessages["course_language"]}
                                helperText={languageHelperText}
                                fullWidth
                                margin="normal"
                                value={courseLanguage}
                                onChange={(e) => setCourseLanguage(e.target.value)}
                                select
                            >
                                {languageOptions.map((languageOption) => (
                                        <MenuItem key={languageOption.value} value={languageOption.value}>
                                                {languageOption.label}
                                        </MenuItem>
                                ))}
                            </RequiredTextField>
              <RequiredTextField label={localeMessages["course_description"]} helperText={descriptionHelperText} fullWidth margin="normal" multiline rows={4} value={courseDescription} onChange={(e) => setCourseDescription(e.target.value)} />
              <TextField
                label={localeMessages["target_audience"]}
                fullWidth
                margin="normal"
                multiline
                rows={3}
                value={courseTargetAudience}
                onChange={(e) => setCourseTargetAudience(e.target.value)}
                dir={direction}
              />
              <Divider sx={{ my: 2 }} />
              <Box sx={{ mt: 1 }}>
                    <FormControlLabel
                            control={<Switch checked={isPublic} disabled={!organizationIsPublic} onChange={(e) => setIsPublic(e.target.checked)} dir={direction} />}
                            label={localeMessages["course_is_public"]}
                            sx={{ m: 0 }}
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            {organizationIsPublic ? localeMessages["course_is_public_helper_text"] : localeMessages["course_is_public_disabled_helper_text"]}
                    </Typography>
              </Box>
              <Box sx={{ mt: 2 }}>
                    <FormControlLabel
                            control={<Switch checked={sendCertificate} onChange={(e) => setSendCertificate(e.target.checked)} dir={direction} />}
                            label={localeMessages["course_send_certificate"]}
                            sx={{ m: 0 }}
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            {localeMessages["course_send_certificate_helper_text"]}
                    </Typography>
              </Box>
              <Divider sx={{ my: 2 }} />
                            <Box sx={{ mt: 2 }}>
                                <Stack direction="row" sx={{ mb: 1, justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="subtitle1">{localeMessages["external_references"]}</Typography>
                    <Button
                        onClick={handleAddExternalReference}
                        disabled={externalReferences.length >= MAX_EXTERNAL_REFERENCES}
                    >
                        {localeMessages["add_external_reference"]}
                    </Button>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {localeMessages["external_references_helper_text"]}
                </Typography>
                <Stack spacing={2}>
                    {externalReferences.map((reference, index) => (
                        <Box
                            key={index}
                            sx={{
                                display: 'grid',
                                gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1fr) minmax(0, 1fr) auto' },
                                columnGap: { xs: 0, md: 2 },
                                rowGap: { xs: 0, md: 0 },
                                alignItems: 'start',
                            }}
                        >
                            <TextField
                                label={localeMessages["reference_name"]}
                                fullWidth
                                margin="none"
                                value={reference.name}
                                onChange={(e) => handleExternalReferenceChange(index, 'name', e.target.value)}
                                error={Boolean(externalReferenceErrors[index]?.name)}
                                helperText={externalReferenceErrors[index]?.name ? localeMessages["reference_name_required_helper_text"] : ' '}
                                sx={{
                                    mb: 0,
                                    '&.MuiTextField-root': {
                                        mt: 0,
                                    },
                                    '&.MuiTextField-root + .MuiTextField-root': {
                                        mt: 0,
                                    },
                                }}
                                dir={direction}
                            />
                            <TextField
                                label={localeMessages["reference_url"]}
                                fullWidth
                                margin="none"
                                type="url"
                                value={reference.url}
                                onChange={(e) => handleExternalReferenceChange(index, 'url', e.target.value)}
                                error={Boolean(externalReferenceErrors[index]?.url)}
                                helperText={externalReferenceErrors[index]?.url ? localeMessages["reference_url_required_helper_text"] : ' '}
                                sx={{
                                    mt: 0,
                                    '&.MuiTextField-root': {
                                        mt: 0,
                                    },
                                }}
                                dir={direction}
                            />
                            <Button color="error" onClick={() => handleRemoveExternalReference(index)} sx={{ mt: { xs: 0.5, md: 0 }, justifySelf: { xs: 'flex-start', md: 'start' }, alignSelf: { xs: 'flex-start', md: 'center' } }}>
                                {localeMessages["remove"]}
                            </Button>
                        </Box>
                    ))}
                </Stack>
              </Box>
              <Divider sx={{ my: 2 }} />
              <FormControlLabel
                control={<Switch onChange={() => switchImapConnection()} checked={addImapConnection} dir={direction} />}
                label={localeMessages["add_imap_connection"]} sx={{ m: 0 }} />
                <Tooltip title={localeMessages["imap_connection_tooltip"]}>
                    <IconButton size="small">
                        <InfoOutlinedIcon fontSize="small" />
                    </IconButton>
                </Tooltip>


              { addImapConnection && <Box sx={{ py: 2 }}>
                    <AddImapConnectionForm
                        onChangeCallback={(id) => setImapConnectionId(id)}
                        activeOrganizationId={activeOrganizationId}
                        initialImapConnectionId={imapConnectionId}
                    />
              </Box>}
              {newslettersEnabled && (<>
              <Divider sx={{ my: 2 }} />
                <FormControlLabel
                    control={<Switch onChange={() => setAddNewsletter(!addNewsletter)} checked={addNewsletter} dir={direction} />}
                    label={localeMessages["add_newsletter"]} sx={{ m: 0 }} />
                <Tooltip title={localeMessages["newsletter_tooltip"]}>
                    <IconButton size="small">
                        <InfoOutlinedIcon fontSize="small" />
                    </IconButton>
                </Tooltip>
                {addNewsletter && (
                    <Box sx={{ py: 2 }}>
                        <AddNewsletterForm
                            onChangeCallback={(id) => setNewsletterId(id)}
                            activeOrganizationId={activeOrganizationId}
                            initialNewsletterIdId={newsletterId}
                            showCreate={createNewsletterEnabled}
                        />
                    </Box>
                )}
              </>)}
              <Divider sx={{ my: 2 }} />
              <Box sx={{ mt: 1 }}>
                <FormControlLabel
                    control={<Switch onChange={() => setAddInstructors(!addInstructors)} checked={addInstructors} dir={direction} />}
                    label={localeMessages["add_instructors"]}
                    sx={{ m: 0 }}
                />
                <Tooltip title={localeMessages["instructors_tooltip"]}>
                    <IconButton size="small">
                        <InfoOutlinedIcon fontSize="small" />
                    </IconButton>
                </Tooltip>
              </Box>
              {addInstructors && <Box sx={{ py: 2 }}>
                <AddInstructorsSection
                    onChangeCallback={(ids) => setSelectedInstructorIds(ids)}
                    activeOrganizationId={activeOrganizationId}
                    initialInstructorIds={selectedInstructorIds}
                />
              </Box>}
              <Divider sx={{ my: 2 }} />
              <Box>
                <ImageUpload organizationId={activeOrganizationId} initialUrl={imageUrl} onUploadSuccess={(data) => {
                    setImageUrl(data.file_url);
                    setImageServerPath(data.file_path);
                }} />
              </Box>
                            <Box sx={{ mt: 2, textAlign: 'right' }}>
                <Button onClick={cancelCallback} sx={{ mr: 1 }}>{localeMessages["cancel"]}</Button>
                { createMode && <Button variant="contained" onClick={() => handleCreateCourse()} sx={{ boxShadow: 'none' }}>{localeMessages["create"]}</Button> }
                { !createMode && <Button variant="contained" onClick={() => handleUpdateCourse()} sx={{ boxShadow: 'none' }}>{localeMessages["update"]}</Button> }
              </Box></>}
            </Box>);
}

export default CourseForm;
