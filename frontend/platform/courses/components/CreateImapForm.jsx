import RequiredTextField from "../../../src/components/RequiredTextField"
import { Alert, Box, Button, Chip, Stack, TextField, Tooltip } from "@mui/material"
import { useState } from "react"
import { useAppContext } from '../../../src/render.jsx';
import { getCookie } from '../../../src/utils';


const CreateImapForm = ({ onSuccess, activeOrganizationId }) => {

    const [email, setEmail] = useState("");
    const [emailHelperText, setEmailHelperText] = useState("");
    const [server, setServer] = useState("");
    const [serverHelperText, setServerHelperText] = useState("");
    const [port, setPort] = useState("");
    const [folders, setFolders] = useState(["inbox"]);
    const [folderInput, setFolderInput] = useState("");
    const [folderHelperText, setFolderHelperText] = useState("");
    const [portHelperText, setPortHelperText] = useState("");
    const [password, setPassword] = useState("");
    const [passwordHelperText, setPasswordHelperText] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const { localeMessages, apiBaseUrl } = useAppContext();

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
                port: port,
                folders: folders.includes("inbox") ? folders : ["inbox", ...folders],
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

    const handleAddFolder = () => {
        const normalizedFolder = folderInput.trim();
        if (!normalizedFolder) {
            setFolderHelperText("Folder name cannot be empty.");
            return;
        }
        if (folders.includes(normalizedFolder)) {
            setFolderHelperText("Folder already added.");
            return;
        }
        setFolders((prevFolders) => [...prevFolders, normalizedFolder]);
        setFolderInput("");
        setFolderHelperText("");
    }

    const handleRemoveFolder = (folderToRemove) => {
        if (folderToRemove === "inbox") {
            return;
        }
        setFolders((prevFolders) => prevFolders.filter((folder) => folder !== folderToRemove));
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
        <Box sx={{ mt: 2 }}>
            <Stack direction="row" spacing={1}>
                <Tooltip title={localeMessages["add_folder_helper_text"]}>
                <TextField
                    label="Add folder"
                    size="small"
                    fullWidth
                    value={folderInput}
                    onChange={(e) => {
                        setFolderInput(e.target.value);
                        if (folderHelperText) {
                            setFolderHelperText("");
                        }
                    }}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") {
                            e.preventDefault();
                            handleAddFolder();
                        }
                    }}
                    helperText={folderHelperText || "'inbox' is required and cannot be removed."}
                    error={Boolean(folderHelperText)}
                /></Tooltip>
                <Button variant="outlined" size="small" onClick={handleAddFolder} sx={{ boxShadow: 'none', height: '40px' }}>
                    {localeMessages["add"]}
                </Button>
            </Stack>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ marginTop: 1.5 }}>
                {folders.map((folder) => (
                    <Chip
                        key={folder}
                        label={folder}
                        color={folder === "inbox" ? "primary" : "default"}
                        variant={folder === "inbox" ? "filled" : "outlined"}
                        onDelete={folder === "inbox" ? undefined : () => handleRemoveFolder(folder)}
                    />
                ))}
            </Stack>
        </Box>
        <Box sx={{ mt: 2, textAlign: 'right' }}>
            <Button variant="contained" onClick={() => handleCreateImap()} sx={{ boxShadow: 'none' }}>
                {localeMessages["add"]}
            </Button>
        </Box>
    </>)
}

export default CreateImapForm;
