import { Button, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';


const EnableCourseSwitchPopup = ({ courseId, action, courseTitle, handleClose, handleSuccess}) => {
    const activeOrganizationId = localStorage.getItem('activeOrganizationId');
    const { localeMessages, apiBaseUrl } = useAppContext();

    const updateCourseState = () => {
        apiClient.post(`${apiBaseUrl}/organizations/${activeOrganizationId}/courses/${courseId}/`, { enabled: action === 'enable', image: "SKIP" })
        .then(data => {
            console.log('Course state updated successfully:', data);
            handleSuccess(data);
            handleClose();
        })
        .catch(error => {
            console.error('Error updating course state:', error);
        });
    }

    return <><DialogTitle id="alert-dialog-title">
          {localeMessages[`${action}_course`].replace('COURSE_NAME', courseTitle)}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
           { localeMessages[`course_${action}_confirmation`].replace('COURSE_NAME', courseTitle) }
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>{localeMessages["cancel"]}</Button>
          <Button onClick={updateCourseState} autoFocus variant="contained">
            {localeMessages["continue"]}
          </Button>
        </DialogActions></>;
}

export default EnableCourseSwitchPopup;
