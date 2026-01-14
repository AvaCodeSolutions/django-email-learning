import React from 'react';
import { Alert, Box, Button, Typography } from '@mui/material';
import RequiredTextField from  '../../src/components/RequiredTextField.jsx';

const EnrollmentForm = ({course_title, course_slug, onCancel}) => {

    const emailRef = React.useRef('');
    const [errorMessage, setErrorMessage] = React.useState('');

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
            // TODO: call the public API to enroll the user when the endpoint is ready
            console.log('Enrolling with email:', emailRef.current.value, 'for course:', course_slug);
        }
    }

    return (<Box sx={{padding: 4}}>
        <Typography variant='h3'> Enroll for {course_title}</Typography>
        {errorMessage && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage}</Alert>}
        <RequiredTextField label="email" name="email" type="email" fullWidth margin="normal" inputRef={emailRef} onKeyDown={(e) => {
            if (e.key === 'Enter') {
                enroll();
            }
        }} />
        <input type="hidden" name="course_slug" value={course_slug} />
        <Box sx={{ mt: 2, textAlign: 'right' }}>
        <Button variant="outlined" sx={{ mr: 1 }} onClick={onCancel}>
            Cancel
        </Button>
        <Button variant="contained" color="primary" type="submit" onClick={enroll}>
            Submit
        </Button>
        </Box>
        </Box>);

};

export default EnrollmentForm;
