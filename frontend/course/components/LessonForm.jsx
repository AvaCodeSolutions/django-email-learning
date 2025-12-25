import { useState, useEffect, use } from 'react';
import { Alert, Box, Button, Typography, Select, MenuItem, Tooltip } from '@mui/material';
import RequiredTextField from '../../src/components/RequiredTextField.jsx';
import ContentEditor from '../../src/components/ContentEditor';
import { getCookie } from '../../src/utils.js';

function LessonForm({ header, initialTitle, initialContent, onContentChange, cancelCallback, successCallback, courseId, lessonId, initialWaitingPeriod, contentId }) {
    const [title, setTitle] = useState(initialTitle || "");
    const [content, setContent] = useState(initialContent || "");
    const [waitingPeriod, setWaitingPeriod] = useState(initialWaitingPeriod ? initialWaitingPeriod.period : 1);
    const [waitingPeriodUnit, setWaitingPeriodUnit] = useState(initialWaitingPeriod ? initialWaitingPeriod.type : "days");
    const [titleHelperText, setTitleHelperText] = useState("");
    const [contentHelperText, setContentHelperText] = useState("");
    const [errorMessage, setErrorMessage] = useState("");

    const userRole = localStorage.getItem('userRole');
    const apiBaseUrl = localStorage.getItem('apiBaseUrl');
    const orgId = localStorage.getItem('activeOrganizationId');

    const addLesson = () =>{
        if (!validateForm()) {
            setErrorMessage("Please fix the errors in the form before submitting.");
            return;
        }

        console.log("Adding lesson to course ID:", courseId);
        fetch(apiBaseUrl + '/organizations/' + orgId + '/courses/' + courseId + '/contents/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                content: {
                    title: title,
                    content: content,
                    type: 'lesson'
                },
                waiting_period: {"period": waitingPeriod, "type": waitingPeriodUnit},
            }),
        })
        .then((response) => response.json())
        .then((data) => {
            console.log('Lesson created successfully:', data);
            setContent("");
            setTitle("");
            successCallback();
        })
        .catch((error) => {
            console.error('Error creating lesson:', error);
        });
    }

    const updateLesson = () => {
        if (!validateForm()) {
            setErrorMessage("Please fix the errors in the form before submitting.");
            return;
        }

        console.log("Updating lesson ID:", lessonId);

        fetch(apiBaseUrl + '/organizations/' + orgId + '/courses/' + courseId + '/contents/' + contentId + '/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                lesson: {
                    title: title,
                    content: content,
                },
                waiting_period: {"period": waitingPeriod, "type": waitingPeriodUnit},
            }),
        })
        .then((response) => {
            console.log(response)
            if (response.status === 200) {
                console.log('Lesson updated successfully');
                successCallback();
            }
        })
        .catch((error) => {
            console.error('Error updating lesson:', error);
        });
    }


    useEffect(() => {
        onContentChange(content);
    }, [content]);

    const handleContentChange = (newContent) => {
        setContent(newContent);
    }

    const cancel = () => {
        setContent("");
        setTitle("");
        cancelCallback();
    }

    const validateForm = () => {
        let isValid = true;
        if (!title) {
            setTitleHelperText("Lesson title is required.");
            isValid = false;
        } else {
            setTitleHelperText("");
        }
        if (!content) {
            setContentHelperText("Lesson content is required.");
            isValid = false;
        } else {
            setContentHelperText("");
        }
        return isValid;
    }

    return (
        <Box sx={{ p: 3 }}>
        <Typography variant="h2" sx={{ my: 2, fontSize: '1.5rem' }}>{header}</Typography>
        { errorMessage && (
            <Alert severity="error" sx={{ marginBottom: "10px" }}>
                {errorMessage}
            </Alert>
        )}
        <RequiredTextField value={title} label="Lesson Title" name="lesson_title" sx={{ width: '100%' }} onChange={(e) => setTitle(e.target.value)} helperText={titleHelperText} disabled={userRole === 'viewer'} />
        <Box sx={{ my: 2 }}>
        <ContentEditor initialContent={content} contentUpdateCallback={handleContentChange} disabled={userRole === 'viewer'} />
        <Typography color="errorText.main" sx={{ marginTop: 1, fontSize: '0.75rem' }}>
            {contentHelperText}
        </Typography>
        </Box>
        <Tooltip
        placement="right"
        title="Set the amount of time that we should wait after the previous lesson or quiz submission before sending this lesson.">
        <RequiredTextField
            label="Waiting Period"
            name="waiting_period"
            type="number"
            value={waitingPeriod}
            onChange={(e) => setWaitingPeriod(e.target.value)}
            sx={{ width: '200px', mr: 2 }}
            inputProps={{ min: 1 }}
            disabled={userRole === 'viewer'}
        />
        <Select size="small" value={waitingPeriodUnit} onChange={(e) => setWaitingPeriodUnit(e.target.value)} name="waiting_period_unit" sx={{ width: '150px' }} disabled={userRole === 'viewer'}>
            <MenuItem value="days">Days</MenuItem>
            <MenuItem value="hours">Hours</MenuItem>
        </Select>
        </Tooltip>
        <Box mt={2} textAlign="right">
        <Button variant="outlined" sx={{ mr: 1 }} onClick={cancel}>
            Back
        </Button>
        {userRole !== 'viewer' && <Button type="submit" variant="contained" onClick={() => {if(!lessonId) { addLesson(); } else { updateLesson(); }}}>
            Save Lesson
        </Button>}
        </Box>
        </Box>
    );
}

export default LessonForm;
