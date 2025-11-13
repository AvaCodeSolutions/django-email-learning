import RequiredTextField from "../../src/components/RequiredTextField"
import { Alert, Box, Button } from "@mui/material"
import { useState } from "react"
import { getCookie } from '../../src/utils';


const CreateImapForm = ({ onSuccess, activeOrganizationId }) => {

    const [email, setEmail] = useState("");
    const [emailHelperText, setEmailHelperText] = useState("");
    const [server, setServer] = useState("");
    const [serverHelperText, setServerHelperText] = useState("");
    const [port, setPort] = useState("");
    const [portHelperText, setPortHelperText] = useState("");
    const [password, setPassword] = useState("");
    const [passwordHelperText, setPasswordHelperText] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const apiBaseUrl = localStorage.getItem('apiBaseUrl');

    const handleCreateImap = () => {
        const isValid = validateForm();
        if (!isValid) {
            return;
        }
        fetch(apiBaseUrl + '/organizations/' + activeOrganizationId + '/imap-connections/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                email: email,
                password: password,
                server: server,
                port: port
            }),
        })
        .then((response) => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then((data) => {
            if (onSuccess) {
                onSuccess(data);
            }
            setEmail("");
            setErrorMessage("");
            setPassword("");
            setServer("");
            setPasswordHelperText("");
            setServerHelperText("");
            setEmailHelperText("");
        })
        .catch((error) => {
            console.error('Error creating IMAP connection:', error);
            setErrorMessage("Failed to create IMAP connection. Please try again.");
        });
    };

    const isValidEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    const validateForm = () => {
        let isValid = true;
        if (!email) {
            setEmailHelperText("Email is required");
            isValid = false;
        } else if (isValidEmail(email) === false) {
            setEmailHelperText("Email is invalid");
            isValid = false;
        } else {
            setEmailHelperText("");
        }
        if (!password) {
            setPasswordHelperText("Password is required");
            isValid = false;
        } else {
            setPasswordHelperText("");
        }
        if (!server) {
            setServerHelperText("Server is required");
            isValid = false;
        } else {
            setServerHelperText("");
        }
        if (!port) {
            setPortHelperText("Port is required");
            isValid = false;
        } else if (isNaN(port) || parseInt(port) <= 0) {
            setPortHelperText("Port must be a positive number");
            isValid = false;
        } else {
            setPortHelperText("");
        }
        return isValid;
    }

    return (<>
        { errorMessage && <Alert severity="error" sx={{ marginBottom: 2 }} >{errorMessage}</Alert> }
        <RequiredTextField label="Email" helperText={emailHelperText} sx={{ width: "100%" }} value={email} onChange={(e) => setEmail(e.target.value)} />
        <RequiredTextField label="Password" helperText={passwordHelperText} type="password" sx={{ width: "100%", marginTop: 2 }} value={password} onChange={(e) => setPassword(e.target.value)} />
        <RequiredTextField label="Server" helperText={serverHelperText} sx={{ width: "100%", marginTop: 2 }} value={server} onChange={(e) => setServer(e.target.value)} />
        <RequiredTextField label="Port" helperText={portHelperText} sx={{ width: "100%", marginTop: 2 }} value={port} onChange={(e) => setPort(e.target.value)} />
        <Box mt={2} textAlign="right">
            <Button variant="contained" onClick={() => handleCreateImap()} sx={{ boxShadow: 'none' }}>
                Add
            </Button>
        </Box>
    </>)
}

export default CreateImapForm;
