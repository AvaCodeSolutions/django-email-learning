import React from 'react';
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import RequiredTextField from  '../../src/components/RequiredTextField.jsx';
import { getCookie } from '../../src/utils.js';


const EnrollmentForm = ({course_title, course_slug, organization_id, endpoint, onCancle, onComplete}) => {

    const emailRef = React.useRef('');
    const [errorMessage, setErrorMessage] = React.useState('');
    const [isProcessing, setIsProcessing] = React.useState(false);

    const validateForm = () => {
        const email = emailRef.current.value;
        if (!email) {
            setErrorMessage('Email is required');
            return false;
        }
        // Simple email regex for validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            setErrorMessage('Please enter a valid email address');
            return false;
        }
        setErrorMessage('');
        return true;
    }

    const enroll = () => {
        if (validateForm()) {
            setIsProcessing(true);
            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    email: emailRef.current.value,
                    course_slug: course_slug,
                    organization_id: organization_id,
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Handle success
                setIsProcessing(false);
                onComplete();
            })
            .catch(error => {
                setIsProcessing(false);
                setErrorMessage('Enrollment failed. Please try again.');
            });
        }
    }

    return (<Box sx={{padding: 4, minWidth: '400px'}}>
        <Typography variant='h3'> Enroll for {course_title}</Typography>
        { isProcessing ? <Typography variant='body1' sx={{ mt: 2 }}><CircularProgress enableTrackSlot size="30px" /></Typography> : <>
        {errorMessage && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage}</Alert>}
        <RequiredTextField label="email" name="email" type="email" fullWidth margin="normal" inputRef={emailRef} onKeyDown={(e) => {
            if (e.key === 'Enter') {
                enroll();
            }
        }} />
        <input type="hidden" name="course_slug" value={course_slug} />
        <Box sx={{ mt: 2, textAlign: 'right' }}>
        <Button variant="outlined" sx={{ mr: 1 }} onClick={onCancle}>
            Cancel
        </Button>
        <Button variant="contained" color="primary" type="submit" onClick={enroll}>
            Submit
        </Button>
        </Box>
        </>}
        </Box>);

};

export default EnrollmentForm;
