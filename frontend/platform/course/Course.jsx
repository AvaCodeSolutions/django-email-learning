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
import DeleteContentForm from './components/DeleteContentForm.jsx';
import { getCookie } from '../../src/utils.js';


function Course() {
    const platformBaseUrl = localStorage.getItem('platformBaseUrl');
    const [dialogOpen, setDialogOpen] = useState(false)
    const [dialogContent, setDialogContent] = useState(null)
    const [lessonCache, setLessonCache] = useState("")
    const [contentLoaded, setContentLoaded] = useState(false)
    const [dialogMaxWidth, setDialogMaxWidth] = useState('lg');

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

    const deletContent = (contentId) => {
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${course_id}/contents/${contentId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
        })
            .then(response => {
                if (response.ok) {
                    setContentLoaded(false);
                } else {
                    console.error('Error deleting content:', response.statusText);
                }
            })
            .catch(error => console.error('Error deleting content:', error));
        setDialogMaxWidth('lg');
        setDialogOpen(false);
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
                            header={localeMessages["update_lesson"]}
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
        if (event.type === 'delete_content') {
            setDialogContent(<DeleteContentForm content={event.content} onDelete={deletContent} onCancel={() => {setDialogOpen(false); setDialogMaxWidth('lg');}} />);
            setDialogMaxWidth('sm');
            setDialogOpen(true);
        }
    }

    return (
        <Base
            breadCrumbList={[
                {label: localeMessages["course_management"], href: platformBaseUrl + '/courses', index: 0},
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
                    {userRole !== 'viewer' && <><Button variant="contained" startIcon={<DescriptionIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2 }} onClick={() => {
                        setDialogContent(<LessonForm
                            header={localeMessages["new_lesson"]}
                            initialContent={lessonCache}
                            onContentChange={setLessonCache}
                            cancelCallback={() => setDialogOpen(false)}
                            successCallback={resetDialog}
                            courseId={course_id} />);
                        setDialogOpen(true);}}>{localeMessages["add_lesson"]}</Button>
                    <Button variant="contained" startIcon={<BallotIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2, marginLeft: 1, marginRight: 1 }} onClick={() => {
                        setDialogContent(<QuizForm
                            cancelCallback={() => setDialogOpen(false)}
                            successCallback={resetDialog}
                            courseId={course_id} />);
                        setDialogOpen(true);}}>{localeMessages["add_quiz"]}</Button></> }
                    <ContentTable courseId={course_id} loaded={contentLoaded} eventHandler={(event) => tableEventHandler(event)} />
                </Box>
            </Grid>

            <Dialog open={dialogOpen} onClose={handleClose} fullWidth maxWidth={dialogMaxWidth}>
                {dialogContent}
            </Dialog>
        </Base>
    )
}

render({children: <Course />});
