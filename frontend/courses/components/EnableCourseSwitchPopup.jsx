import { Button, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";
import { getCookie } from '../../src/utils';

const EnableCourseSwitchPopup = ({ courseId, action, courseTitle, handleClose, handleSuccess}) => {

    const apiBaseUrl = localStorage.getItem('apiBaseUrl');
    const activeOrganizationId = localStorage.getItem('activeOrganizationId');

    const updateCourseState = () => {
        fetch(`${apiBaseUrl}/organizations/${activeOrganizationId}/courses/${courseId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ enabled: action === 'enable' })
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
          {`${action.charAt(0).toUpperCase() + action.slice(1)} ${courseTitle} Course`}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
           { `Are you sure you want to ${action} the course "${courseTitle}"?` }
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={updateCourseState} autoFocus variant="contained">
            Continue
          </Button>
        </DialogActions></>;
}

export default EnableCourseSwitchPopup;
