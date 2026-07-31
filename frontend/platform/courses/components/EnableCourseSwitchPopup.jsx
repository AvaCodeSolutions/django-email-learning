import { useState } from 'react';
import { Alert, Button, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';


const EnableCourseSwitchPopup = ({ courseId, action, courseTitle, handleClose, handleSuccess}) => {
    const activeOrganizationId = localStorage.getItem('activeOrganizationId');
    const { localeMessages, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const updateCourseState = () => {
        setSubmitting(true);
        setError('');
        apiClient.post(`${apiBaseUrl}/organizations/${activeOrganizationId}/courses/${courseId}/`, { enabled: action === 'enable', image: "SKIP" })
        .then(data => {
            handleSuccess(data);
            handleClose();
        })
        .catch(error => {
            console.error('Error updating course state:', error);
            setError(error?.body?.error || localeMessages["server_error"]);
        })
        .finally(() => setSubmitting(false));
    }

    return <><DialogTitle id="alert-dialog-title">
          {localeMessages[`${action}_course`].replace('COURSE_NAME', courseTitle)}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
           { localeMessages[`course_${action}_confirmation`].replace('COURSE_NAME', courseTitle) }
          </DialogContentText>
          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={submitting}>{localeMessages["cancel"]}</Button>
          <Button onClick={updateCourseState} autoFocus variant="contained" disabled={submitting}>
            {localeMessages["continue"]}
          </Button>
        </DialogActions></>;
}

export default EnableCourseSwitchPopup;
