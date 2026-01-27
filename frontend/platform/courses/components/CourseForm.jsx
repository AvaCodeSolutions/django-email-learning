import { Alert, Box, Button, FormControlLabel, Switch, Tooltip, Typography } from '@mui/material';
import RequiredTextField  from '../../../src/components/RequiredTextField.jsx';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import IconButton from '@mui/material/IconButton';
import AddImapConnectionForm from './AddImapConnectionForm.jsx';
import { useEffect, useState } from 'react';
import { getCookie } from '../../../src/utils.js';

function CourseForm({successCallback, failureCallback, cancelCallback, activeOrganizationId, createMode, courseId}) {

    const [courseTitle, setCourseTitle] = useState("")
    const [courseSlug, setCourseSlug] = useState("")
    const [courseDescription, setCourseDescription] = useState("")
    const [addImapConnection, setAddImapConnection] = useState(false)
    const [imapConnectionId, setImapConnectionId] = useState(null)
    const [titleHelperText, setTitleHelperText] = useState("")
    const [slugHelperText, setSlugHelperText] = useState("")
    const [descriptionHelperText, setDescriptionHelperText] = useState("")
    const [errorMessage, setErrorMessage] = useState("")

    const apiBaseUrl = localStorage.getItem('apiBaseUrl');

    const switchImapConnection = () => {
        if (addImapConnection) {
            setAddImapConnection(false)
        } else {
            setAddImapConnection(true)
        }
    }

    useEffect(() => {
        if (!createMode && courseId) {
            fetch(apiBaseUrl + '/organizations/' + activeOrganizationId + '/courses/' + courseId + '/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'include', // Include cookies in the request
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                setCourseTitle(data.title);
                setCourseSlug(data.slug);
                setCourseDescription(data.description);
                if (data.imap_connection_id) {
                    setImapConnectionId(data.imap_connection_id);
                    setAddImapConnection(true);
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
        if (!courseTitle) {
            setTitleHelperText(localeMessages["title_required_helper_text"]);
            isValid = false;
        } else {
            setTitleHelperText("");
        }
        if (!courseSlug) {
            setSlugHelperText(localeMessages["slug_required_helper_text"]);
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

        return isValid;
    }

    const handleUpdateCourse = () => {
        const isValid = validateForm()
        if (!isValid) {
            return
        }
        fetch(apiBaseUrl + '/organizations/' + activeOrganizationId + '/courses/' + courseId + '/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'include', // Include cookies in the request
        body: JSON.stringify({
            title: courseTitle,
            // slug is not updatable
            description: courseDescription,
            imap_connection_id: imapConnectionId && addImapConnection? parseInt(imapConnectionId) : null,
            reset_imap_connection: !addImapConnection || imapConnectionId == null
        }),
        })
        .then(response => {
            if (!response.ok) {
                if (response.status >= 500) {
                    setErrorMessage("Server error occurred. Please try again later.");
                }
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
            successCallback(data);
        })
        .catch((error) => {
            console.error('Error:', error);
            if (error)
            failureCallback(error);
        });
    };

    const handleCreateCourse = () => {
        const isValid = validateForm()
        if (!isValid) {
            return
        }
        fetch(apiBaseUrl + '/organizations/' + activeOrganizationId + '/courses/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'include', // Include cookies in the request
        body: JSON.stringify({
            title: courseTitle,
            slug: courseSlug,
            description: courseDescription,
            imap_connection_id: imapConnectionId ? parseInt(imapConnectionId) : null
        }),
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 409) {
                    setErrorMessage("A course with this title or slug already exists.");
                }
                else if (response.status >= 500) {
                    setErrorMessage("Server error occurred. Please try again later.");
                }
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
            // Optionally reset form fields here
            setCourseTitle("");
            setCourseSlug("");
            setCourseDescription("");
            successCallback(data);
        })
        .catch((error) => {
            console.error('Error:', error);
            if (error)
            failureCallback(error);
        });
    };

    return (<Box p={2}>
              { errorMessage && <Alert severity="error" sx={{ marginBottom: "10px" }}>{errorMessage}</Alert> }
              <RequiredTextField label={localeMessages["course_title"]} helperText={titleHelperText} fullWidth margin="normal" value={courseTitle} onChange={(e) => setCourseTitle(e.target.value)} />
              <RequiredTextField label={localeMessages["course_slug"]} helperText={slugHelperText} fullWidth margin="normal" value={courseSlug} onChange={(e) => setCourseSlug(e.target.value)} {...(!createMode ? { disabled: true } : {})} />

              <RequiredTextField label={localeMessages["course_description"]} helperText={descriptionHelperText} fullWidth margin="normal" multiline rows={4} value={courseDescription} onChange={(e) => setCourseDescription(e.target.value)} />
              <FormControlLabel
                control={<Switch onChange={() => switchImapConnection()} checked={addImapConnection} dir={direction} />}
                label={localeMessages["add_imap_connection"]} sx={{ m: 0 }} />
                <Tooltip title={localeMessages["imap_connection_tooltip"]}>
                    <IconButton size="small">
                        <InfoOutlinedIcon fontSize="small" />
                    </IconButton>
                </Tooltip>


              { addImapConnection && <Box py={2}>
                    <AddImapConnectionForm
                        onChangeCallback={(id) => setImapConnectionId(id)}
                        activeOrganizationId={activeOrganizationId}
                        initialImapConnectionId={imapConnectionId}
                    />
                </Box>}
              <Box mt={2} textAlign="right">
                <Button onClick={cancelCallback} sx={{ mr: 1 }}>Cancel</Button>
                { createMode && <Button variant="contained" onClick={() => handleCreateCourse()} sx={{ boxShadow: 'none' }}>{localeMessages["create"]}</Button> }
                { !createMode && <Button variant="contained" onClick={() => handleUpdateCourse()} sx={{ boxShadow: 'none' }}>{localeMessages["update"]}</Button> }
              </Box>
            </Box>);
}

export default CourseForm;
