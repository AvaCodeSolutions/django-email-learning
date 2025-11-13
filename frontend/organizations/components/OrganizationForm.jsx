import { Box, Button, DialogActions, TextField } from "@mui/material";
import RequiredTextField  from "../../src/components/RequiredTextField.jsx";
import { useState } from "react";

function OrganizationForm({ successCallback, failureCallback, cancelCallback, createMode }) {
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [nameHelperText, setNameHelperText] = useState("");
    const [descriptionHelperText, setDescriptionHelperText] = useState("");

    const apiBaseUrl = localStorage.getItem('apiBaseUrl');

    const handleCreate = () => (event) => {
        event.preventDefault();
        // Implement organization creation logic here
        // On success, call successCallback with organization data
        // On failure, call failureCallback with error
        successCallback({ id: 1, name: "New Organization" });
    }
    return (
        <Box p={2}>
            <RequiredTextField label="Name" helperText={nameHelperText} fullWidth margin="normal" value={name} onChange={(e) => setName(e.target.value)} />
            <RequiredTextField label="Description" helperText={descriptionHelperText} fullWidth margin="normal" multiline rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
            Logo: File upload component
            <DialogActions>
                <Button onClick={cancelCallback}>Cancel</Button>
                <Button type="submit" color="primary" onClick={handleCreate()}>
                    {createMode ? 'Create' : 'Update'} Organization
                </Button>
            </DialogActions>
        </Box>
    );
}

export default OrganizationForm;
