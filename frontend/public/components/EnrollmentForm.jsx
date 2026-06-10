import React, { useEffect } from 'react';
import { Alert, Box, Button, CircularProgress, Typography, Dialog } from '@mui/material';
import RequiredTextField from  '../../src/components/RequiredTextField.jsx';
import { useAppContext } from '../../src/render.jsx';
import apiClient from '../../src/apiClient.js';


const EnrollmentForm = ({course_title, course_slug, organization_id, endpoint, onCancle, onComplete, autoFocusEmail = false}) => {

    const emailRef = React.useRef('');
    const [errorMessage, setErrorMessage] = React.useState('');
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [showReloadDialog, setShowReloadDialog] = React.useState(false);
    const { localeMessages, termsOfServiceUrl } = useAppContext();

    React.useEffect(() => {
        if (!autoFocusEmail) {
            return;
        }
        const timeoutId = setTimeout(() => {
            emailRef.current?.focus();
        }, 150);

        return () => clearTimeout(timeoutId);
    }, [autoFocusEmail]);

    const validateForm = () => {
        const email = emailRef.current.value;
        if (!email) {
            setErrorMessage(localeMessages["email_required"]);
            return false;
        }
        // Simple email regex for validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            setErrorMessage(localeMessages["email_invalid"]);
            return false;
        }
        setErrorMessage('');
        return true;
    }

    const enroll = () => {
        if (validateForm()) {
            setIsProcessing(true);
            apiClient.post(endpoint, {
                email: emailRef.current.value,
                course_slug: course_slug,
                organization_id: organization_id,
            })
            .then(() => {
                // Handle success
                setIsProcessing(false);
                onComplete();
            })
            .catch(error => {
                setIsProcessing(false);
                if (error instanceof apiClient.ApiError && error.status === 403) {
                    setShowReloadDialog(true);
                    return;
                }
                setErrorMessage(localeMessages['enrollment_failed']);
            });
        }
    }

    return (<Box sx={{padding: 4}}>
        <Typography variant='h3'> {localeMessages['enrol_for_course'].replace('COURSE_NAME', course_title)}</Typography>
        { isProcessing ? <Typography variant='body1' sx={{ mt: 2 }}><CircularProgress enableTrackSlot size="30px" /></Typography> : <>
        {errorMessage && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage}</Alert>}
        <RequiredTextField label={localeMessages['email']} name="email" type="email" fullWidth margin="normal" inputRef={emailRef} onKeyDown={(e) => {
            if (e.key === 'Enter') {
                enroll();
            }
        }} />
        {termsOfServiceUrl && (
            <Typography
                variant='caption'
                sx={{
                    display: 'block',
                    mt: 2.5,
                    mb: 1.5,
                    color: 'text.secondary',
                    lineHeight: 1.6,
                    '& a': {
                        color: 'primary.main',
                        textDecoration: 'underline',
                        fontWeight: 500,
                    },
                }}
            >
                <span dangerouslySetInnerHTML={{ __html: localeMessages['terms_of_service_confirmation'].replace('TERMS_OF_SERVICE_URL', termsOfServiceUrl) }} />
            </Typography>
        )}
        <input type="hidden" name="course_slug" value={course_slug} />
        <Box sx={{ mt: 1.5, textAlign: 'right' }}>
        <Button variant="outlined" sx={{ mx: 1 }} onClick={onCancle}>
            {localeMessages['cancel']}
        </Button>
        <Button variant="contained" color="primary" type="submit" onClick={enroll}>
            {localeMessages['submit']}
        </Button>
        </Box>
        </>}
        <Dialog open={showReloadDialog} onClose={() => setShowReloadDialog(false)}>
            <Box sx={{ padding: 4 }}>
                <Typography variant='h6'>{localeMessages['in_app_browser_or_disabled_cookies']}</Typography>
                <Button variant="contained" color="primary" onClick={() => window.location.reload()}>
                    {localeMessages['continue']}
                </Button>
            </Box>
        </Dialog>
        </Box>

    );

};

export default EnrollmentForm;
