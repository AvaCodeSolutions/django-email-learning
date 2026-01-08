import './styles.scss'

import 'vite/modulepreload-polyfill'
import render from '../../src/render.jsx';
import Base from '../../src/components/Base.jsx'
import FilterListIcon from '@mui/icons-material/FilterList';
import DescriptionIcon from '@mui/icons-material/Description';
import BallotIcon from '@mui/icons-material/Ballot';
import { useState } from 'react';
import { Box, Grid, Button, Dialog } from '@mui/material'
import LessonForm from './components/LessonForm.jsx';
import QuizForm from './components/QuizForm.jsx';
import ContentTable from './components/ContentTable.jsx';
import { getCookie } from '../../src/utils.js';


function Course() {
    const platformBaseUrl = localStorage.getItem('platformBaseUrl');
    const [dialogOpen, setDialogOpen] = useState(false)
    const [dialogContent, setDialogContent] = useState(null)
    const [lessonCache, setLessonCache] = useState("")
    const [contentLoaded, setContentLoaded] = useState(false)

    const userRole = localStorage.getItem('userRole');
    const apiBaseUrl = localStorage.getItem('apiBaseUrl');
    const organizationId = localStorage.getItem('activeOrganizationId');

    const resetDialog = () => {
        setDialogOpen(false);
        setContentLoaded(false);
    }

    const handleClose = (event, reason) => {
        if (reason !== "backdropClick" && reason !== "escapeKeyDown") {
            setDialogOpen(false);
        }
    }
    const getContent = async (contentId, ) => {
        console.log("Fetching content with ID:", contentId);
        const response = await fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${course_id}/contents/${contentId}/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
        });
        if (response.ok) {
            const data = await response.json();
            console.log("Content data:", data);
            return data;
        } else {
            console.error('Error fetching content:', response.statusText);
            return null;
        }
    }

    const translateOptions = (options) => {
        return options.map((opt) => ({
            optionText: opt.text,
            isCorrect: opt.is_correct,
            editMode: false
        }));
    }

    const translateQuestions = (questions) => {
        return questions.map((q) => ({
            text: q.text,
            options: translateOptions(q.answers),
        }));
    }

    const tableEventHandler = async (event) => {
        console.log("Event triggered from ContentTable", event);
        if (event.type === 'content_loaded') {
            setContentLoaded(true);
        }
        if (event.type === 'content_clicked') {
            const content = await getContent(event.content_id);
            if (content.type == 'lesson') {
            console.log("Opening lesson editor for content:", content);
            setDialogOpen(true);
            setDialogContent(<LessonForm
                            header="Update Lesson"
                            initialTitle={content.lesson.title}
                            initialContent={content.lesson.content}
                            onContentChange={setLessonCache}
                            cancelCallback={() => {setLessonCache(""); setDialogOpen(false);}}
                            successCallback={resetDialog}
                            courseId={course_id}
                            lessonId={content.lesson.id}
                            initialWaitingPeriod={content.waiting_period}
                            contentId={content.id} />);
            } else if (content.type == 'quiz') {
                console.log("Opening quiz editor for content:", content);
                setDialogOpen(true);
                setDialogContent(<QuizForm
                                cancelCallback={() => setDialogOpen(false)}
                                successCallback={resetDialog}
                                courseId={course_id}
                                quizId={content.quiz.id}
                                contentId={content.id}
                                initialTitle={content.quiz.title}
                                initialRequiredScore={content.quiz.required_score}
                                initialQuestions={translateQuestions(content.quiz.questions)}
                                initialWaitingPeriod={content.waiting_period}
                                initialStrategy={content.quiz.selection_strategy}
                                initialDeadlineDays={content.quiz.deadline_days}
                                 />);
            }
        }
        if (event.type === 'content_reordered') {
            console.log("Reordering contents with new order:", event.new_order);
            fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${course_id}/contents/reorder/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    ordered_content_ids: event.new_order
                })
            }).then(response => {
                if (response.ok) {
                    console.log('Contents reordered successfully');
                } else {
                    console.error('Error reordering contents:', response.statusText);
                }
            })
            .catch(error => console.error('Error reordering contents:', error));
        }
    }

    return (
        <Base
            breadCrumbList={[
                {label: 'Course Management', href: platformBaseUrl + '/courses', index: 0},
                {label: course_title, href: '#', index: 1}
            ]}
            bottomDrawerParams={{
                icon: <FilterListIcon />,
                children: <div>Filter Options Here</div>,
            }}
            showOrganizationSwitcher={false}
        >
            <Grid size={{xs: 12, md: 9}} py={2} pl={2}>
                <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300 }}>
                    {userRole !== 'viewer' && <><Button variant="contained" startIcon={<DescriptionIcon />} sx={{ marginBottom: 2 }} onClick={() => {
                        setDialogContent(<LessonForm
                            header="New Lesson"
                            initialContent={lessonCache}
                            onContentChange={setLessonCache}
                            cancelCallback={() => setDialogOpen(false)}
                            successCallback={resetDialog}
                            courseId={course_id} />);
                        setDialogOpen(true);}}>Add a Lesson</Button>
                    <Button variant="contained" startIcon={<BallotIcon />} sx={{ marginBottom: 2, marginLeft: 1 }} onClick={() => {
                        setDialogContent(<QuizForm
                            cancelCallback={() => setDialogOpen(false)}
                            successCallback={resetDialog}
                            courseId={course_id} />);
                        setDialogOpen(true);}}>Add a Quiz</Button></> }
                    <ContentTable courseId={course_id} loaded={contentLoaded} eventHandler={(event) => tableEventHandler(event)} />
                </Box>
            </Grid>

            <Dialog open={dialogOpen} onClose={handleClose} fullWidth maxWidth="lg" sx={{ xs: { width: '100%' }, md: { width: '80%' }, lg: { maxWidth: '70%' } }}>
                {dialogContent}
            </Dialog>
        </Base>
    )
}

render({children: <Course />});
