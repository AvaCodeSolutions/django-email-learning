import RequiredTextField from "../../../src/components/RequiredTextField"
import { Alert, Box, Button } from "@mui/material"
import { useState } from "react"
import { getCookie } from '../../../src/utils';


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
            setEmailHelperText(localeMessages["email_required_helper_text"]);
            isValid = false;
        } else if (isValidEmail(email) === false) {
            setEmailHelperText(localeMessages["invalid_email_helper_text"]);
            isValid = false;
        } else {
            setEmailHelperText("");
        }
        if (!password) {
            setPasswordHelperText(localeMessages["password_required_helper_text"]);
            isValid = false;
        } else {
            setPasswordHelperText("");
        }
        if (!server) {
            setServerHelperText(localeMessages["server_required_helper_text"]);
            isValid = false;
        } else {
            setServerHelperText("");
        }
        if (!port) {
            setPortHelperText(localeMessages["port_required_helper_text"]);
            isValid = false;
        } else if (isNaN(port) || parseInt(port) <= 0) {
            setPortHelperText(localeMessages["invalid_port_helper_text"]);
            isValid = false;
        } else {
            setPortHelperText("");
        }
        return isValid;
    }

    return (<>
        { errorMessage && <Alert severity="error" sx={{ marginBottom: 2 }} >{errorMessage}</Alert> }
        <RequiredTextField label={localeMessages["email"]} helperText={emailHelperText} fullWidth value={email} onChange={(e) => setEmail(e.target.value)} />
        <RequiredTextField label={localeMessages["password"]} helperText={passwordHelperText} type="password" fullWidth sx={{ marginTop: 2 }} value={password} onChange={(e) => setPassword(e.target.value)} />
        <RequiredTextField label={localeMessages["server"]} helperText={serverHelperText} fullWidth sx={{ marginTop: 2 }} value={server} onChange={(e) => setServer(e.target.value)} />
        <RequiredTextField label={localeMessages["port"]} helperText={portHelperText} fullWidth sx={{ marginTop: 2 }} value={port} onChange={(e) => setPort(e.target.value)} />
        <Box mt={2} textAlign="right">
            <Button variant="contained" onClick={() => handleCreateImap()} sx={{ boxShadow: 'none' }}>
                {localeMessages["add"]}
            </Button>
        </Box>
    </>)
}

export default CreateImapForm;
