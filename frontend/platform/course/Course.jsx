import './styles.scss'

import 'vite/modulepreload-polyfill'
import render, { useAppContext } from '../../src/render.jsx';
import Base from '../../src/components/Base.jsx'
import EnrollMenu from './components/EnrollMenu.jsx';
import DescriptionIcon from '@mui/icons-material/Description';
import BallotIcon from '@mui/icons-material/Ballot';
import AssignmentIcon from '@mui/icons-material/Assignment';
import ViewListIcon from '@mui/icons-material/ViewList';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import InsightsIcon from '@mui/icons-material/Insights';
import { useState, useEffect } from 'react';
import { Box, Grid, Button, Dialog, LinearProgress, Typography, Alert, Skeleton, Tabs, Tab, Badge } from '@mui/material'
import { useTheme } from '@mui/material/styles';
import ContentTable from './components/ContentTable.jsx';
import SubmittedAssignmentsSection from './components/SubmittedAssignmentsSection.jsx';
import { PieChart } from '@mui/x-charts/PieChart'
import { BarChart } from '@mui/x-charts/BarChart';
import { getCookie } from '../../src/utils.js';
import { lazy, Suspense } from "react";

const QuizForm = lazy(() => import("./components/QuizForm.jsx"));
const LessonForm = lazy(() => import("./components/LessonForm.jsx"));
const AssignmentForm = lazy(() => import("./components/AssignmentForm.jsx"));
const DeleteContentForm = lazy(() => import("./components/DeleteContentForm.jsx"));


function Course() {
    const { courseTitle, courseId, localeMessages, direction, userRole, isInstructor, isInstructore, apiBaseUrl, platformBaseUrl, customComponent } = useAppContext();
    const [dialogOpen, setDialogOpen] = useState(false)
    const [dialogContent, setDialogContent] = useState(null)
    const [contentLoaded, setContentLoaded] = useState(false)
    const [dialogMaxWidth, setDialogMaxWidth] = useState('lg');
    const [enrollmentsCount, setEnrollmentsCount] = useState(null);
    const [weeklyStats, setWeeklyStats] = useState(null);
    const [isEnrollmentsLoading, setIsEnrollmentsLoading] = useState(true);
    const [isWeeklyStatsLoading, setIsWeeklyStatsLoading] = useState(true);
    const [dialogCloseOnBackdropClick, setDialogCloseOnBackdropClick] = useState(false);
    const [activeTab, setActiveTab] = useState('content');
    const [pendingAssignmentsCount, setPendingAssignmentsCount] = useState(0);

    const [pageSuccessMessage, setPageSuccessMessage] = useState('');

    const organizationId = localStorage.getItem('activeOrganizationId');

    const theme = useTheme();

    const totalEnrollments = enrollmentsCount
        ? enrollmentsCount.reduce((sum, item) => sum + item.value, 0)
        : 0;

    const enrollmentsPieData = enrollmentsCount
        ? enrollmentsCount.map((item) => {
            const percentage = totalEnrollments > 0
                ? Math.round((item.value / totalEnrollments) * 100)
                : 0;
            return {
                ...item,
                label: `${item.label} (${percentage}%)`,
            };
        })
        : null;

    const activeEnrollments = enrollmentsCount
        ? (enrollmentsCount.find((item) => item.label === localeMessages["active"])?.value || 0)
        : 0;
    const activePercentage = totalEnrollments > 0
        ? Math.round((activeEnrollments / totalEnrollments) * 100)
        : 0;

    const currentWeekEnrollments = weeklyStats && weeklyStats.length > 0
        ? weeklyStats.reduce((sum, stat) => sum + stat.count, 0)
        : 0;

    const hasEnrollmentsChartData = !!(enrollmentsPieData && totalEnrollments > 0);
    const hasWeeklyChartData = !!(weeklyStats && weeklyStats.some((stat) => stat.count > 0));
    const canSeeSubmittedAssignments = Boolean(
        isInstructore ?? isInstructor
    );


    const resetDialog = () => {
        setDialogOpen(false);
        setContentLoaded(false);
    }

    const refreshEnrollmentAnalytics = () => {
        setIsEnrollmentsLoading(true);
        setIsWeeklyStatsLoading(true);

        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
        })
            .then(response => response.json())
            .then(data => {
                setEnrollmentsCount([
                    { label: localeMessages["unverified"], value: data.enrollments_count.unverified, color: theme.palette.indigo[200] },
                    { label: localeMessages["active"], value: data.enrollments_count.active, color: theme.palette.primary.main },
                    { label: localeMessages["deactivated"], value: data.enrollments_count.deactivated, color: theme.palette.grey[300] },
                    { label: localeMessages["completed"], value: data.enrollments_count.completed, color: theme.palette.secondary.main },
                ]);
            })
            .catch(error => console.error('Error fetching course data:', error))
            .finally(() => setIsEnrollmentsLoading(false));

        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/enrollments/statistics/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
        })
            .then(response => response.json())
            .then(data => {
                setWeeklyStats(data.statistics);
            })
            .catch(error => console.error('Error fetching enrollment statistics:', error))
            .finally(() => setIsWeeklyStatsLoading(false));
    }

    const refreshPendingAssignmentsCount = () => {
        const endpoint = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/submitted_assignments/?status=pending_review`;
        fetch(endpoint, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
        })
            .then(response => response.json())
            .then(data => {
                setPendingAssignmentsCount((data.submissions || []).length);
            })
            .catch(error => {
                console.error('Error fetching pending assignments count:', error);
                setPendingAssignmentsCount(0);
            });
    }

    useEffect(() => {
        refreshEnrollmentAnalytics();
        if (canSeeSubmittedAssignments) {
            refreshPendingAssignmentsCount();
        }
        window.ContentListAPI = {
            refresh: () => setContentLoaded(false)
        }
        window.DialogAPI = {
            show: (content) => {
                setDialogContent(content);
                setDialogOpen(true);
            },
            close: () => setDialogOpen(false),
            setMaxWidth: (maxWidth) => setDialogMaxWidth(maxWidth || 'md'),
            setCloseOnBackdropClick: (closeOnBackdropClick) => setDialogCloseOnBackdropClick(!!closeOnBackdropClick),
            getDialogBackdropClickSetting: () => dialogCloseOnBackdropClick,
        }
    }, []);

    useEffect(() => {
        if (canSeeSubmittedAssignments) {
            refreshPendingAssignmentsCount();
        }
    }, [canSeeSubmittedAssignments, organizationId, courseId]);

    useEffect(() => {
        if (!canSeeSubmittedAssignments && activeTab === 'submitted_assignments') {
            setActiveTab('content');
        }
    }, [canSeeSubmittedAssignments, activeTab]);

    const handleEnrollMenuSuccess = (msg) => {
        setPageSuccessMessage(msg);
        setTimeout(() => setPageSuccessMessage(''), 4000);
        refreshEnrollmentAnalytics();
    }

    const handleClose = (event, reason) => {
        if (dialogCloseOnBackdropClick) {
            setDialogOpen(false);
        }
        if (reason !== "backdropClick" && reason !== "escapeKeyDown") {
            setDialogOpen(false);
        }
    }

    const getContent = async (contentId, ) => {
        console.log("Fetching content with ID:", contentId);
        const response = await fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`, {
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
            id: opt.id,
            optionText: opt.text,
            isCorrect: opt.is_correct,
            editMode: false
        }));
    }

    const translateQuestions = (questions) => {
        return questions.map((q) => ({
            id: q.id,
            text: q.text,
            options: translateOptions(q.answers),
        }));
    }

    const deletContent = (contentId) => {
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`, {
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
            setDialogOpen(false);
            setDialogMaxWidth('lg');
            const content = await getContent(event.content_id);
            if (content.type == 'lesson') {
            console.log("Opening lesson editor for content:", content);
            setDialogOpen(true);
            setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><LessonForm
                            header={localeMessages["update_lesson"]}
                            initialTitle={content.lesson.title}
                            initialContent={content.lesson.content}
                            cancelCallback={() => {setDialogOpen(false);}}
                            successCallback={() => setContentLoaded(false)}
                            courseId={courseId}
                            lessonId={content.lesson.id}
                            initialWaitingPeriod={content.waiting_period}
                            contentId={content.id} /></Suspense>);
            } else if (content.type == 'quiz') {
                console.log("Opening quiz editor for content:", content);
                setDialogOpen(true);
                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><QuizForm
                                cancelCallback={() => setDialogOpen(false)}
                                successCallback={resetDialog}
                                courseId={courseId}
                                quizId={content.quiz.id}
                                contentId={content.id}
                                initialTitle={content.quiz.title}
                                initialRequiredScore={content.quiz.required_score}
                                initialQuestions={translateQuestions(content.quiz.questions)}
                                initialWaitingPeriod={content.waiting_period}
                                initialStrategy={content.quiz.selection_strategy}
                                initialDeadlineDays={content.quiz.deadline_days}
                                initialLimitedAttempts={content.quiz.limited_attempts}
                                initialIsBlocking={content.quiz.is_blocking}
                                initialReminderIntervalDays={content.quiz.reminder_interval_days}
                                 /></Suspense>);
            } else if (content.type == 'assignment') {
                console.log("Opening assignment editor for content:", content);
                setDialogOpen(true);
                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><AssignmentForm
                                header={localeMessages["update_assignment"]}
                                cancelCallback={() => setDialogOpen(false)}
                                successCallback={resetDialog}
                                courseId={courseId}
                                assignmentId={content.assignment.id}
                                contentId={content.id}
                                initialTitle={content.assignment.title}
                                initialDescription={content.assignment.description}
                                initialIsBlocking={content.assignment.is_blocking}
                                initialDeadlineDays={content.assignment.deadline_days}
                                initialRequiresTextSubmission={content.assignment.requires_text_submission}
                                initialRequiresFileSubmission={content.assignment.requires_file_submission}
                                initialReminderIntervalDays={content.assignment.reminder_interval_days}
                                initialWaitingPeriod={content.waiting_period}
                                /></Suspense>);
            }
        }
        if (event.type === 'content_reordered') {
            console.log("Reordering contents with new order:", event.new_order);
            fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/reorder/`, {
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
            setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><DeleteContentForm content={event.content} onDelete={deletContent} onCancel={() => {setDialogOpen(false); setDialogMaxWidth('lg');}} /></Suspense>);
            setDialogMaxWidth('sm');
            setDialogOpen(true);
        }
    }

    return (
        <Base
            breadCrumbList={[
                {label: localeMessages["course_management"], href: platformBaseUrl + '/courses', index: 0},
                {label: courseTitle, href: '#', index: 1}
            ]}
            showOrganizationSwitcher={false}
        >
            {pageSuccessMessage && (
                <Box
                    sx={{
                        position: 'fixed',
                        top: 88,
                        insetInlineEnd: 24,
                        zIndex: (muiTheme) => muiTheme.zIndex.snackbar,
                        width: { xs: 'calc(100% - 32px)', sm: 420 },
                    }}
                >
                    <Alert severity="success" onClose={() => setPageSuccessMessage('')}>
                        {pageSuccessMessage}
                    </Alert>
                </Box>
            )}
            <Grid size={{xs: 12}} sx={{ px: 2, pt: 2, pb: 3 }}>
                <Box
                    sx={{
                        mb: 3,
                        p: 2,
                        border: '1px solid',
                        borderColor: 'border.main',
                        borderRadius: 2,
                        backgroundColor: 'background.box',
                    }}
                >
                    <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                                {localeMessages["total_enrollments"] || 'Total Enrollments'}
                            </Typography>
                            <Typography variant="h6">{totalEnrollments}</Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                                {localeMessages["active"] || 'Active'}
                            </Typography>
                            <Typography variant="h6">{activePercentage}%</Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                                {localeMessages["weekly_enrollments"] || 'Weekly Enrollments'}
                            </Typography>
                            <Typography variant="h6">{currentWeekEnrollments}</Typography>
                        </Grid>
                    </Grid>
                </Box>
                <Box sx={{ p: 3, border: '1px solid', borderColor: 'border.main', backgroundColor: 'background.box', borderRadius: 2, minHeight: 300 }}>
                    <Tabs
                        value={activeTab}
                        onChange={(_, value) => {
                            setActiveTab(value);
                            if (value === 'content') {
                                setContentLoaded(false);
                            }
                        }}
                        sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
                    >
                        <Tab
                            value="content"
                            icon={<ViewListIcon fontSize="small" />}
                            iconPosition="start"
                            label={localeMessages["tab_manage_course_content"] || 'Manage Course Content'}
                        />
                        {canSeeSubmittedAssignments && (
                            <Tab
                                value="submitted_assignments"
                                icon={<TaskAltIcon fontSize="small" />}
                                iconPosition="start"
                                label={
                                    <Badge
                                        color="primary"
                                        badgeContent={pendingAssignmentsCount}
                                        max={99}
                                        overlap="rectangular"
                                        sx={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            '& .MuiBadge-badge': {
                                                position: 'static',
                                                transform: 'none',
                                                marginInlineStart: 0.75,
                                            },
                                        }}
                                    >
                                        <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center' }}>
                                            {localeMessages["tab_submitted_assignments"] || 'Submitted Assignments'}
                                        </Box>
                                    </Badge>
                                }
                            />
                        )}
                        <Tab
                            value="analytics"
                            icon={<InsightsIcon fontSize="small" />}
                            iconPosition="start"
                            label={localeMessages["tab_course_analytics"] || 'Course Analytics'}
                        />
                    </Tabs>

                    {activeTab === 'content' && (
                        <>
                            {userRole !== 'viewer' && <><Button variant="contained" startIcon={<DescriptionIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2 }} onClick={() => {
                                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><LessonForm
                                    header={localeMessages["new_lesson"]}
                                    cancelCallback={() => setDialogOpen(false)}
                                    successCallback={() => setContentLoaded(false)}
                                    courseId={courseId} /></Suspense>);
                                setDialogOpen(true);}}>{localeMessages["add_lesson"]}</Button>
                            <Button variant="contained" startIcon={<BallotIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2, marginLeft: 1, marginRight: 1 }} onClick={() => {
                                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><QuizForm
                                    cancelCallback={() => setDialogOpen(false)}
                                    successCallback={resetDialog}
                                    courseId={courseId} /></Suspense>);
                                setDialogOpen(true);}}>{localeMessages["add_quiz"]}</Button>
                            <Button variant="contained" startIcon={<AssignmentIcon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2, marginLeft: 1, marginRight: 1 }} onClick={() => {
                                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><AssignmentForm
                                    header={localeMessages["new_assignment"]}
                                    cancelCallback={() => setDialogOpen(false)}
                                    successCallback={resetDialog}
                                    courseId={courseId} /></Suspense>);
                                setDialogOpen(true);}}>{localeMessages["add_assignment"]}</Button>
                            {userRole === 'admin' && <EnrollMenu successCallback={handleEnrollMenuSuccess} />}
                            </> }
                            {customComponent && <Box className="custom-component-wrapper" sx={{ display: customComponent.container_display }} dangerouslySetInnerHTML={{ __html: customComponent.html }}></Box>}
                            <ContentTable courseId={courseId} loaded={contentLoaded} eventHandler={(event) => tableEventHandler(event)} />
                        </>
                    )}

                    {canSeeSubmittedAssignments && activeTab === 'submitted_assignments' && (
                        <SubmittedAssignmentsSection
                            onPendingCountChange={(count) => setPendingAssignmentsCount(count)}
                        />
                    )}

                    {activeTab === 'analytics' && (
                        <>
                            <Alert severity="info" sx={{ mb: 2 }}>
                                {localeMessages["course_analytics_tab_info"] || 'Course analytics are shown below.'}
                            </Alert>
                            <Grid container spacing={3} sx={{ alignItems: 'stretch' }}>
                                <Grid size={{xs: 12, lg: 6}} sx={{ display: 'flex', flexDirection: 'column' }}>
                                    <Box sx={{ py: 3, border: '1px solid', borderColor: 'border.main', borderRadius: 2, backgroundColor: 'background.box', flex: 1 }}>
                                        <Typography variant="h6" align='center'>{localeMessages["enrollments_distribution"]}</Typography>
                                        <Typography variant="body2" align='center' sx={{ mt: 1, mb: 2, color: 'text.secondary' }}>
                                            {(localeMessages["total_enrollments"]) + ': ' + totalEnrollments}
                                        </Typography>
                                        {isEnrollmentsLoading ? (
                                            <Box sx={{ px: 2 }}>
                                                <Skeleton variant="circular" width={180} height={180} sx={{ mx: 'auto', my: 2 }} />
                                                <Skeleton variant="text" width="80%" sx={{ mx: 'auto' }} />
                                                <Skeleton variant="text" width="60%" sx={{ mx: 'auto' }} />
                                            </Box>
                                        ) : hasEnrollmentsChartData ? (
                                            <PieChart
                                                height={300}
                                                series={[
                                                {
                                                    data: enrollmentsPieData,
                                                    innerRadius: '50%',
                                                    arcLabelMinAngle: 20,
                                                    highlightScope: { fade: 'global', highlight: 'item' },
                                                },
                                                ]}
                                                skipAnimation={false}
                                                margin={{
                                                    bottom: 20,
                                                    top: 20,
                                                    left: 5,
                                                    right: 5,
                                                }}
                                                slotProps={{
                                                    legend: {
                                                    direction: 'row',
                                                    position: { vertical: 'bottom', horizontal: 'middle' },
                                                    padding: 0,
                                                    },
                                                }}
                                            />
                                        ) : (
                                            <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    {localeMessages['no_data_yet'] || 'No data yet'}
                                                </Typography>
                                            </Box>
                                        )}
                                    </Box>
                                </Grid>
                                <Grid size={{xs: 12, lg: 6}} sx={{ display: 'flex', flexDirection: 'column' }}>
                                    <Box sx={{ py: 3, border: '1px solid', borderColor: 'border.main', borderRadius: 2, backgroundColor: 'background.box', flex: 1 }}>
                                        <Typography variant="h6" align='center'>{localeMessages["weekly_enrollments"]}</Typography>
                                        {isWeeklyStatsLoading ? (
                                            <Box sx={{ px: 2 }}>
                                                <Skeleton variant="rectangular" height={220} sx={{ borderRadius: 1, my: 2 }} />
                                                <Skeleton variant="text" width="75%" sx={{ mx: 'auto' }} />
                                            </Box>
                                        ) : hasWeeklyChartData ? (
                                            <BarChart
                                                margin={{
                                                    top: 60,
                                                }}
                                                xAxis={[{data: weeklyStats.map((stat) => stat.date)}]}
                                                series={[{ data: weeklyStats.map((stat) => stat.count), color: theme.palette.secondary.main }]}
                                                height={300}
                                            />
                                        ) : (
                                            <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    {localeMessages['no_data_yet'] || 'No data yet'}
                                                </Typography>
                                            </Box>
                                        )}
                                    </Box>
                                </Grid>
                            </Grid>
                        </>
                    )}
                </Box>
            </Grid>

            <Dialog open={dialogOpen} onClose={handleClose} fullWidth maxWidth={dialogMaxWidth}>
                {dialogContent}
            </Dialog>
        </Base>
    )
}

render({children: <Course />});
