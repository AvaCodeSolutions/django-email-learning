import render from "../../src/render";

import { useState } from "react";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { Alert } from "@mui/material";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import WorkspacePremiumIcon from '@mui/icons-material/WorkspacePremium';
import { useAppContext } from "../../src/render.jsx";

const CertificateForm = () => {
    const [fullName, setFullName] = useState("");
    const [error, setError] = useState("");
    const [nameSubmitted, setNameSubmitted] = useState(false);
    const { localeMessages, apiEndpoint, token, csrfToken } = useAppContext();
    const [ certificateUrl, setCertificateUrl ] = useState("");

    const handleSubmit = (event) => {
        event.preventDefault();
        if (!fullName.trim()) {
            setError(localeMessages['full_name_required']);
            return;
        }
        setError("");
        fetch(`${apiEndpoint}?token=${token}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({ token: token, name: fullName }),
        })
        .then((response) => {
            if (!response.ok) {
                throw new Error(localeMessages['error_sending_data']);
            }
            return response.json();
        })
        .then((data) => {
            setCertificateUrl(data.certificate_url);
        })
        .then(() => {
            setNameSubmitted(true);
        })
        .catch((error) => {
            setError(error.message);
        });
    };

    return (<Box sx={{ minHeight: "100vh", display: "flex", alignItems: "flex-start", justifyContent: "center", pt: "22vh", px: 2, bgcolor: "background.main" }}>
        <Container
            maxWidth="sm"
            sx={{
                mt: 0,
                py: 4,
                px: { xs: 3, sm: 4 },
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 3,
                boxShadow: 2,
                bgcolor: "background.paper",
            }}
        >
        <Box sx={{ display: 'flex', alignItems: 'center', my: 4, justifyContent: 'center' }}>
            <WorkspacePremiumIcon color="secondary" sx={{ fontSize: 50, mr: 1 }} />
            <Typography variant="h4" component="h1">
                {localeMessages['form_title']}
            </Typography>
        </Box>
        <Typography variant="body1" gutterBottom>
            {localeMessages['form_intro']}
        </Typography>
        { !nameSubmitted ? <Box component="form" method="POST" action="" sx={{ mt: 2 }} onSubmit={handleSubmit}>
            <TextField
                fullWidth
                label={localeMessages['full_name']}
                name="full_name"
                required
                margin="normal"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
            />
            {error && <Alert severity="error">{error}</Alert>}
            <Button type="submit" variant="contained" color="secondary" sx={{ mt: 3, mx: "auto", display: "block", px: 4, fontSize: '1.1rem' }}>
                {localeMessages['submit']}
            </Button>
        </Box> : <Alert severity="success" sx={{ mt: 2 }}>{localeMessages['form_submission_success']}</Alert>}
        {certificateUrl && (
            <Box sx={{ mt: 2, mx: "auto", display: "flex", justifyContent: "center" }}>
                <Button
                    variant="contained"
                    color="secondary"
                    href={certificateUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{ px: 4, fontSize: '1.1rem' }}
                >
                    {localeMessages['view_certificate']}
                </Button>
            </Box>
        )}
    </Container>
    </Box>);
};

render({children: <CertificateForm />});
