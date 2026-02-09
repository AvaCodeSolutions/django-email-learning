import { Alert, Button, Box, DialogActions, DialogContent, DialogContentText, DialogTitle, Typography } from "@mui/material";
import { useState } from "react"
import { getCookie } from '../../../src/utils';
import WarningIcon from '@mui/icons-material/Warning';


const DeleteUserDialog = ({ user, handleClose, handleSuccess}) => {

    const apiBaseUrl = localStorage.getItem('apiBaseUrl');
    const [errorMessage, setErrorMessage] = useState("");

    const deleteUser = () => {
        fetch(`${apiBaseUrl}/organizations/${user.organization_id}/users/${user.id}/`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
        })
        .then(response => {
          if(response.status != 200) {
            throw new Error("Unhandled network Error! user is not deleted")
          }
          return response.json()}
        )
        .then(data => {
            if (data.error){
              throw new Error(data.error)
            } else {
              console.log('User deleted successfully:', data);
              handleSuccess();
            }
        })
        .catch(error => {
            setErrorMessage(error.message)
        });
    }


    return <><DialogTitle id="alert-dialog-title">
        { errorMessage && <Alert severity="error">{errorMessage}</Alert> }
        <Typography variant="h6" component="span">
          <Box sx={{ display: 'inline-block', alignItems: 'center', mr: 1, mt: 1, pt: 1}}>
            <WarningIcon color="warning" />
          </Box>
          <Box sx={{ display: 'inline-block'}}>
          {localeMessages["delete_user_with_email"].replace("USER_EMAIL", user.email)}
          </Box>
        </Typography>
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
           { localeMessages["user_delete_confirmation"].replace("USER_EMAIL", user.email) }
          </DialogContentText>
          <Alert severity="info" sx={{ mt: 2 }}>{localeMessages["delete_note"]}</Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>{localeMessages["cancel"]}</Button>
          <Button onClick={deleteUser} autoFocus variant="contained">
            <Typography>{localeMessages["delete"]}</Typography>
          </Button>
        </DialogActions></>;
}

export default DeleteUserDialog;
