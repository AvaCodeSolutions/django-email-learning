import { Alert, Button, Box, DialogActions, DialogContent, DialogContentText, DialogTitle, Typography } from "@mui/material";
import { useState } from "react"
import { useAppContext } from '../../../src/render.jsx';
import WarningIcon from '@mui/icons-material/Warning';
import apiClient from '../../../src/apiClient.js';

const DeleteCoursePopup = ({ courseId, courseTitle, handleClose, handleSuccess}) => {
    const { localeMessages, apiBaseUrl } = useAppContext();
    const activeOrganizationId = localStorage.getItem('activeOrganizationId');
    const [showError, setShowError] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");


    const deleteCourse = () => {
        apiClient.del(`${apiBaseUrl}/organizations/${activeOrganizationId}/courses/${courseId}/`)
        .then(data => {
            if (data && data.error){
              throw new Error(data.error)
            } else {
              console.log('Course state deleted successfully:', data);
              handleSuccess();
              handleClose();
            }
        })
        .catch(error => {
            if (error instanceof apiClient.ApiError && error.status === 409 && error.body?.error) {
                setErrorMessage(error.body.error);
            } else {
                setErrorMessage(error.message);
            }
            setShowError(true);
        });
    }

    return <><DialogTitle id="alert-dialog-title">
        { showError && <Alert severity="error">{errorMessage}</Alert> }
        <Typography variant="h6" component="span">
          <Box sx={{ display: 'inline-block', alignItems: 'center', mr: 1, mt: 1, pt: 1}}>
            <WarningIcon color="warning" />
          </Box>
          <Box sx={{ display: 'inline-block'}}>
          {localeMessages["delete_course"].replace("COURSE_NAME", courseTitle)}
          </Box>
        </Typography>
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
           { localeMessages["course_delete_confirmation"].replace("COURSE_NAME", courseTitle) }
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>{localeMessages["cancel"]}</Button>
          <Button onClick={deleteCourse} autoFocus variant="contained">
            <Typography>{localeMessages["delete"]}</Typography>
          </Button>
        </DialogActions></>;
}

export default DeleteCoursePopup;
