import { Button, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";
import { getCookie } from '../../../src/utils';
import { useAppContext } from '../../../src/render.jsx';


const EnableCourseSwitchPopup = ({ courseId, action, courseTitle, handleClose, handleSuccess}) => {
    const activeOrganizationId = localStorage.getItem('activeOrganizationId');
    const { localeMessages, apiBaseUrl } = useAppContext();

    const updateCourseState = () => {
        fetch(`${apiBaseUrl}/organizations/${activeOrganizationId}/courses/${courseId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ enabled: action === 'enable', image: "SKIP" }),
        })
        .then(response => response.json())
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
