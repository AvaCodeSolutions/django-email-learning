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
import PublicIcon from '@mui/icons-material/Public';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CodeIcon from '@mui/icons-material/Code';
import { useState, useEffect, memo } from 'react';
import { Box, Grid, Button, Dialog, DialogTitle, DialogContent, DialogActions, LinearProgress, Typography, Alert, Tabs, Tab, Badge, Link, IconButton, Tooltip, Switch, FormControlLabel, TextField, InputAdornment, GlobalStyles } from '@mui/material'
import { useTheme } from '@mui/material/styles';
import ContentTable from './components/ContentTable.jsx';
import SubmittedAssignmentsSection from './components/SubmittedAssignmentsSection.jsx';
import CourseAnalyticsSection from './components/CourseAnalyticsSection.jsx';
import { lazy, Suspense } from "react";
import apiClient from '../../src/apiClient.js';
import { getReadableTextColor } from '../../src/utils.js';
import Coloris from '@melloware/coloris';
import '@melloware/coloris/dist/coloris.css';
import EmbedCodeBlock from '../../src/components/EmbedCodeBlock.jsx';
import { sanitizeComponentHtml } from '../../src/sanitizeHtml.js';

const CustomComponentSlot = memo(function CustomComponentSlot({ html, display }) {
  return (
    <Box
      className="custom-component-wrapper"
      sx={{ display, marginBottom: {xs: 1, md: 2} }}
      dangerouslySetInnerHTML={{ __html: sanitizeComponentHtml(html) }}
    />
  );
});

const QuizForm = lazy(() => import("./components/QuizForm.jsx"));
const LessonForm = lazy(() => import("./components/LessonForm.jsx"));
const AssignmentForm = lazy(() => import("./components/AssignmentForm.jsx"));
const DeleteContentForm = lazy(() => import("./components/DeleteContentForm.jsx"));
const EnableCourseSwitchPopup = lazy(() => import("../courses/components/EnableCourseSwitchPopup.jsx"));


function Course() {
    const { courseTitle, courseId, courseEnabled: courseEnabledFromContext, courseHasContent, coursePublicUrl, embeddableEnrollmentEnabled, localeMessages, direction, userRole, isInstructor, apiBaseUrl, platformBaseUrl, customComponent, activeOrganizationBrandColor } = useAppContext();
    const defaultButtonBgColor = activeOrganizationBrandColor || '#4A5EC0';
    const [courseEnabled, setCourseEnabled] = useState(courseEnabledFromContext);
    const [publicUrlCopied, setPublicUrlCopied] = useState(false);
    const [embedDialogOpen, setEmbedDialogOpen] = useState(false);
    const [embedScriptHtml, setEmbedScriptHtml] = useState(null);
    const [embedWidgetHtml, setEmbedWidgetHtml] = useState(null);
    const [embedSnippetLoading, setEmbedSnippetLoading] = useState(false);
    const [embedSnippetError, setEmbedSnippetError] = useState(false);
    const [embedScriptCopied, setEmbedScriptCopied] = useState(false);
    const [embedWidgetCopied, setEmbedWidgetCopied] = useState(false);
    const [includeNewsletterCheck, setIncludeNewsletterCheck] = useState(true);
    const [includeCourseTitle, setIncludeCourseTitle] = useState(true);
    const [includeCourseImage, setIncludeCourseImage] = useState(true);
    const [buttonBgColor, setButtonBgColor] = useState(defaultButtonBgColor);
    const [buttonTextColor, setButtonTextColor] = useState(getReadableTextColor(defaultButtonBgColor));
    const [dialogOpen, setDialogOpen] = useState(false)
    const [dialogContent, setDialogContent] = useState(null)
    const [contentLoaded, setContentLoaded] = useState(false)
    const [dialogMaxWidth, setDialogMaxWidth] = useState('lg');
    const [enrollmentsCount, setEnrollmentsCount] = useState(null);
    const [weeklyStats, setWeeklyStats] = useState(null);
    const [isEnrollmentsLoading, setIsEnrollmentsLoading] = useState(true);
    const [isWeeklyStatsLoading, setIsWeeklyStatsLoading] = useState(true);
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
    const canSeeSubmittedAssignments = Boolean(isInstructor);


    const resetDialog = () => {
        setDialogOpen(false);
        setContentLoaded(false);
    }

    const refreshEnrollmentAnalytics = () => {
        setIsEnrollmentsLoading(true);
        setIsWeeklyStatsLoading(true);

        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/`)
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

        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/enrollments/statistics/`)
            .then(data => {
                setWeeklyStats(data.statistics);
            })
            .catch(error => console.error('Error fetching enrollment statistics:', error))
            .finally(() => setIsWeeklyStatsLoading(false));
    }

    const refreshPendingAssignmentsCount = () => {
        const endpoint = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/submitted_assignments/?status=pending_review`;
        apiClient.get(endpoint)
            .then(data => {
                setPendingAssignmentsCount(data.count ?? (data.items || []).filter(s => s.status === 'pending_review').length);
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

    const openEnableCourseDialog = () => {
        setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><EnableCourseSwitchPopup
            courseId={courseId}
            action="enable"
            courseTitle={courseTitle}
            handleClose={() => {setDialogOpen(false); setDialogMaxWidth('lg');}}
            handleSuccess={() => setCourseEnabled(true)}
        /></Suspense>);
        setDialogMaxWidth('sm');
        setDialogOpen(true);
    }

    const renderDisabledBanner = () => {
        const [before, after] = (localeMessages["course_disabled_banner"] || '').split('ENABLE_LINK');
        return (
            <>
                {before}
                {courseHasContent ? (
                    <Link component="button" type="button" underline="hover" onClick={openEnableCourseDialog}>
                        {localeMessages["course_disabled_banner_link"]}
                    </Link>
                ) : localeMessages["course_disabled_banner_link"]}
                {after}
            </>
        );
    }

    const handleCopyPublicUrl = async () => {
        try {
            await navigator.clipboard.writeText(coursePublicUrl);
            setPublicUrlCopied(true);
            setTimeout(() => setPublicUrlCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy course public URL:', error);
        }
    }

    const handleOpenEmbedDialog = () => {
        setEmbedDialogOpen(true);
        if (embedWidgetHtml || embedSnippetLoading) {
            return;
        }
        setEmbedSnippetLoading(true);
        setEmbedSnippetError(false);
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/embed_snippet/`)
            .then(data => {
                setEmbedScriptHtml(data.script_html);
                setEmbedWidgetHtml(data.widget_html);
            })
            .catch(error => {
                console.error('Failed to load embed snippet:', error);
                setEmbedSnippetError(true);
            })
            .finally(() => setEmbedSnippetLoading(false));
    }

    const handleCloseEmbedDialog = () => {
        setEmbedDialogOpen(false);
    }

    // Loads the del-enroll-form custom element definition (idempotent - the
    // script itself no-ops if already defined) so the preview below the
    // embed code can render the widget exactly as it'll look on the org's
    // own site.
    useEffect(() => {
        if (!embedScriptHtml) {
            return;
        }
        const scriptSrc = embedScriptHtml.match(/src="([^"]+)"/)?.[1];
        if (!scriptSrc || document.querySelector(`script[src="${scriptSrc}"]`)) {
            return;
        }
        const script = document.createElement('script');
        script.src = scriptSrc;
        document.head.appendChild(script);
    }, [embedScriptHtml]);

    // Sets up the two color-picker inputs below. Runs once - Coloris attaches
    // itself to any current/future element matching the selector, so it
    // doesn't need to re-run when the dialog opens/closes.
    useEffect(() => {
        Coloris.init();
        Coloris({
            el: '.coloris-input',
            // MUI's TextField already manages the input's surrounding DOM via
            // React; letting Coloris also wrap the field and inject its own
            // swatch button fights that on every re-render (breaks the
            // picker, throws off alignment). We show our own swatch instead
            // (see the InputAdornment below).
            wrap: false,
            theme: 'polaroid',
            alpha: false,
            format: 'hex',
            onChange: (color, currentEl) => {
                if (currentEl?.id === 'embed-button-bg-color') {
                    setButtonBgColor(color);
                } else if (currentEl?.id === 'embed-button-text-color') {
                    setButtonTextColor(color);
                }
            },
        });
    }, []);

    // Whether the fetched snippet includes a newsletter checkbox at all (i.e.
    // whether the course has a linked newsletter) - independent of whether
    // the user currently wants it included in the snippet they'll copy.
    const hasLinkedNewsletter = Boolean(embedWidgetHtml?.includes('news_letter_check'));
    // Whether the course has an image at all - the "show image" switch only
    // makes sense to offer when there's actually an image to show.
    const hasCourseImage = Boolean(embedWidgetHtml?.includes('course_image='));

    const displayedEmbedWidgetHtml = (() => {
        if (!embedWidgetHtml) {
            return embedWidgetHtml;
        }
        let html = embedWidgetHtml;
        if (hasLinkedNewsletter && !includeNewsletterCheck) {
            html = html.replace(/\s*news_letter_check/, '').replace(/\s*newsletter_title="[^"]*"/, '');
        }
        if (!includeCourseTitle) {
            html = html.replace(/\s*course_title="[^"]*"/, '');
        }
        if (hasCourseImage && !includeCourseImage) {
            html = html.replace(/\s*course_image="[^"]*"/, '');
        }
        const escapedBg = buttonBgColor.replace(/"/g, '&quot;');
        const escapedText = buttonTextColor.replace(/"/g, '&quot;');
        html = html.replace(
            '<del-enroll-form ',
            `<del-enroll-form button_bg_color="${escapedBg}" button_text_color="${escapedText}" `,
        );
        return html;
    })();

    const embedWidgetPreviewHtml = displayedEmbedWidgetHtml?.replace('<del-enroll-form ', '<del-enroll-form preview ');

    const handleCopyEmbedScript = async () => {
        try {
            await navigator.clipboard.writeText(embedScriptHtml);
            setEmbedScriptCopied(true);
            setTimeout(() => setEmbedScriptCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy embed script:', error);
        }
    }

    const handleCopyEmbedWidget = async () => {
        try {
            await navigator.clipboard.writeText(displayedEmbedWidgetHtml);
            setEmbedWidgetCopied(true);
            setTimeout(() => setEmbedWidgetCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy embed widget tag:', error);
        }
    }

    const handleClose = (event, reason) => {
        if (reason !== "backdropClick" && reason !== "escapeKeyDown") {
            setDialogOpen(false);
        }
    }

    const getContent = async (contentId, ) => {
        console.log("Fetching content with ID:", contentId);
        try {
            const data = await apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`);
            console.log("Content data:", data);
            return data;
        } catch (error) {
            console.error('Error fetching content:', error);
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
        apiClient.del(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`)
            .then(() => {
                setContentLoaded(false);
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
            apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/reorder/`, {
                ordered_content_ids: event.new_order
            }).then(() => {
                console.log('Contents reordered successfully');
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
            <Grid size={{xs: 12}} sx={{ px: { xs: 0, md: 2 }, pt: 2, pb: 3 }}>
                {courseEnabled && coursePublicUrl && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', flexWrap: 'wrap', gap: 1, mx: { xs: 2, md: 0 }, mb: 1 }}>
                        <Box
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 0.5,
                                pl: 1.5,
                                pr: 0.5,
                                py: 0.2,
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 2,
                            }}
                        >
                            <Link
                                href={coursePublicUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                underline="none"
                                sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 0.75,
                                    color: 'text.primary',
                                    fontSize: '0.8125rem',
                                    fontWeight: 500,
                                    '&:hover': { color: 'primary.dark' },
                                }}
                            >
                                <PublicIcon fontSize="small" />
                                {localeMessages["view_public_course_page"]}
                            </Link>
                            <Tooltip title={publicUrlCopied ? localeMessages["public_course_link_copied"] : localeMessages["copy_public_course_link"]}>
                                <IconButton
                                    size="small"
                                    onClick={handleCopyPublicUrl}
                                    aria-label={localeMessages["copy_public_course_link"]}
                                    sx={{
                                        borderRadius: '50%',
                                        border: '1px solid transparent',
                                        '&:hover': { borderColor: 'divider', color: 'primary.dark' },
                                    }}
                                >
                                    <ContentCopyIcon fontSize="small" />
                                </IconButton>
                            </Tooltip>
                        </Box>
                        {embeddableEnrollmentEnabled && (
                            <Box
                                component="button"
                                type="button"
                                onClick={handleOpenEmbedDialog}
                                aria-label={localeMessages["add_to_your_site"]}
                                sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 0.75,
                                    pl: 1.5,
                                    pr: 1.5,
                                    py: 0.2,
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    borderRadius: 2,
                                    background: 'none',
                                    cursor: 'pointer',
                                    color: 'text.primary',
                                    fontSize: '0.8125rem',
                                    fontWeight: 500,
                                    fontFamily: 'inherit',
                                    '&:hover': { color: 'primary.dark', borderColor: 'primary.dark' },
                                }}
                            >
                                <CodeIcon fontSize="small" />
                                {localeMessages["add_to_your_site"]}
                            </Box>
                        )}
                    </Box>
                )}
                {courseEnabled === false && (
                    <Alert severity="warning" sx={{ mx: { xs: 2, md: 0 }, mb: 3 }}>
                        {renderDisabledBanner()}
                    </Alert>
                )}
                {courseEnabled !== false && (
                <Box
                    sx={{
                        display: { xs: 'none', md: 'block' },
                        mb: 3,
                        p: 2,
                        borderRadius: { xs: 0, sm: 2 },
                        backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)',
                    }}
                >
                    <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Typography variant="caption" sx={{ color: 'text.primary', display: 'block', mb: 0.5, opacity: { xs: 1 } }}>
                                {localeMessages["total_enrollments"] || 'Total Enrollments'}
                            </Typography>
                            <Typography variant="h6">{totalEnrollments}</Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Typography variant="caption" sx={{ color: 'text.primary', display: 'block', mb: 0.5 }}>
                                {localeMessages["active"] || 'Active'}
                            </Typography>
                            <Typography variant="h6">{activeEnrollments} <Typography component="span" variant="body2" sx={{ color: 'text.secondary' }}>({activePercentage}%)</Typography></Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Typography variant="caption" sx={{ color: 'text.primary', display: 'block', mb: 0.5 }}>
                                {localeMessages["weekly_enrollments"] || 'Weekly Enrollments'}
                            </Typography>
                            <Typography variant="h6">{currentWeekEnrollments}</Typography>
                        </Grid>
                    </Grid>
                </Box>
                )}
                <Box sx={{ px: { xs: 0, md: 2 }, py: 2, backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', borderRadius: { xs: 0, sm: 2 }, minHeight: 300 }}>
                    <Tabs
                        value={activeTab}
                        onChange={(_, value) => {
                            setActiveTab(value);
                            if (value === 'content') {
                                setContentLoaded(false);
                            }
                        }}
                        variant="scrollable"
                        scrollButtons="auto"
                        sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
                    >
                        <Tab
                            value="content"
                            icon={<ViewListIcon fontSize="small" />}
                            iconPosition="start"
                            label={<><Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>{localeMessages["tab_manage_course_content"] || 'Manage Course Content'}</Box><Box component="span" sx={{ display: { xs: 'inline', sm: 'none' } }}>{localeMessages["tab_contents"] || 'Contents'}</Box></>}
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
                                            <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>{localeMessages["tab_submitted_assignments"] || 'Submitted Assignments'}</Box><Box component="span" sx={{ display: { xs: 'inline', sm: 'none' } }}>{localeMessages["tab_assignments"] || 'Assignments'}</Box>
                                        </Box>
                                    </Badge>
                                }
                            />
                        )}
                        <Tab
                            value="analytics"
                            icon={<InsightsIcon fontSize="small" />}
                            iconPosition="start"
                            label={<><Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>{localeMessages["tab_course_analytics"] || 'Course Analytics'}</Box><Box component="span" sx={{ display: { xs: 'inline', sm: 'none' } }}>{localeMessages["tab_analytics"] || 'Analytics'}</Box></>}
                        />
                    </Tabs>

                    {activeTab === 'content' && (
                        <>
                            <Box sx={{ px: 1, display: 'flex', flexDirection: {xs:'column', md: 'row'}, flexWrap: { md: 'wrap' }, alignItems: { xs: 'stretch', md: 'flex-start' }, pb: 2, width: '100%', '& > .MuiButton-root': { flex: { md: '0 0 auto' } } }}>
                                {userRole !== 'viewer' && <><Button variant="contained" startIcon={<DescriptionIcon />} sx={{ marginBottom: {xs: 1, md: 2}, marginInlineEnd: {xs: 0, md: 1} }} onClick={() => {
                                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><LessonForm
                                    header={localeMessages["new_lesson"]}
                                    cancelCallback={() => setDialogOpen(false)}
                                    successCallback={() => setContentLoaded(false)}
                                    courseId={courseId} /></Suspense>);
                                setDialogOpen(true);}}>{localeMessages["add_lesson"]}</Button>
                            <Button variant="contained" startIcon={<BallotIcon />} sx={{ marginBottom: {xs: 1, md: 2}, marginInlineEnd: {xs: 0, md: 1} }} onClick={() => {
                                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><QuizForm
                                    cancelCallback={() => setDialogOpen(false)}
                                    successCallback={resetDialog}
                                    courseId={courseId} /></Suspense>);
                                setDialogOpen(true);}}>{localeMessages["add_quiz"]}</Button>
                            <Button variant="contained" startIcon={<AssignmentIcon />} sx={{ marginBottom: 2, marginInlineEnd: {xs: 0, md: 1} }} onClick={() => {
                                setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><AssignmentForm
                                    header={localeMessages["new_assignment"]}
                                    cancelCallback={() => setDialogOpen(false)}
                                    successCallback={resetDialog}
                                    courseId={courseId} /></Suspense>);
                                setDialogOpen(true);}}>{localeMessages["add_assignment"]}</Button>
                            {customComponent && <CustomComponentSlot html={customComponent.html} display={customComponent.container_display} />}
                            {userRole === 'admin' && <Box sx={{ marginInlineStart: { xs: 0, md: 'auto' }, alignSelf: { xs: 'stretch', md: 'flex-start' } }}><EnrollMenu successCallback={handleEnrollMenuSuccess} courseEnabled={courseEnabled} /></Box>}
                            </> }
                            </Box>
                            <ContentTable courseId={courseId} loaded={contentLoaded} eventHandler={(event) => tableEventHandler(event)} />
                        </>
                    )}

                    {canSeeSubmittedAssignments && activeTab === 'submitted_assignments' && (
                        <SubmittedAssignmentsSection
                            onPendingCountChange={(count) => setPendingAssignmentsCount(count)}
                        />
                    )}

                    {activeTab === 'analytics' && (
                        <CourseAnalyticsSection
                            localeMessages={localeMessages}
                            totalEnrollments={totalEnrollments}
                            isEnrollmentsLoading={isEnrollmentsLoading}
                            hasEnrollmentsChartData={hasEnrollmentsChartData}
                            enrollmentsPieData={enrollmentsPieData}
                            isWeeklyStatsLoading={isWeeklyStatsLoading}
                            hasWeeklyChartData={hasWeeklyChartData}
                            weeklyStats={weeklyStats}
                        />
                    )}
                </Box>
            </Grid>

            <Dialog open={dialogOpen} onClose={handleClose} fullWidth maxWidth={dialogMaxWidth} sx={{ '& .MuiDialog-paper': { mx: { xs: '4px', sm: 4 }, width: { xs: 'calc(100% - 8px)', sm: undefined } }, '& .MuiDialogTitle-root': { px: { xs: 2, sm: 3 } }, '& .MuiDialogContent-root': { px: { xs: 2, sm: 3 } }, '& .MuiDialogActions-root': { px: { xs: 2, sm: 3 } } }}>
                {dialogContent}
            </Dialog>

            {/* Coloris's popup defaults to a lower z-index than MUI's Dialog
                (1300), so without this it opens invisibly behind the dialog. */}
            <GlobalStyles styles={{ '.clr-picker': { zIndex: '1400 !important' } }} />

            <Dialog open={embedDialogOpen} onClose={handleCloseEmbedDialog} fullWidth maxWidth="sm">
                {!embedSnippetLoading && !embedSnippetError && embedWidgetHtml && (
                    <Box sx={{ px: 3, pt: 3 }}>
                        <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                            {localeMessages["embed_preview_title"]}
                        </Typography>
                        <Box
                            sx={{
                                p: 2,
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 1,
                                pointerEvents: 'none',
                                display: 'flex',
                                justifyContent: 'center',
                            }}
                            aria-hidden="true"
                            dangerouslySetInnerHTML={{ __html: sanitizeComponentHtml(embedWidgetPreviewHtml) }}
                        />
                    </Box>
                )}
                <DialogTitle>{localeMessages["embed_customize_form_title"]}</DialogTitle>
                <DialogContent>
                    {!embedSnippetLoading && !embedSnippetError && embedWidgetHtml && (
                        <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
                            <TextField
                                id="embed-button-bg-color"
                                label={localeMessages["embed_button_bg_color_label"]}
                                value={buttonBgColor}
                                onChange={(event) => setButtonBgColor(event.target.value)}
                                size="small"
                                sx={{ mt: '12px' }}
                                slotProps={{
                                    htmlInput: { className: 'coloris-input' },
                                    input: {
                                        startAdornment: (
                                            <InputAdornment position="start">
                                                <Box
                                                    sx={{
                                                        width: 18,
                                                        height: 18,
                                                        borderRadius: '4px',
                                                        border: '1px solid',
                                                        borderColor: 'divider',
                                                        backgroundColor: buttonBgColor,
                                                    }}
                                                />
                                            </InputAdornment>
                                        ),
                                    },
                                }}
                            />
                            <TextField
                                id="embed-button-text-color"
                                label={localeMessages["embed_button_text_color_label"]}
                                value={buttonTextColor}
                                onChange={(event) => setButtonTextColor(event.target.value)}
                                size="small"
                                slotProps={{
                                    htmlInput: { className: 'coloris-input' },
                                    input: {
                                        startAdornment: (
                                            <InputAdornment position="start">
                                                <Box
                                                    sx={{
                                                        width: 18,
                                                        height: 18,
                                                        borderRadius: '4px',
                                                        border: '1px solid',
                                                        borderColor: 'divider',
                                                        backgroundColor: buttonTextColor,
                                                    }}
                                                />
                                            </InputAdornment>
                                        ),
                                    },
                                }}
                            />
                        </Box>
                    )}
                    {!embedSnippetLoading && !embedSnippetError && embedWidgetHtml && (
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={includeCourseTitle}
                                    onChange={(event) => setIncludeCourseTitle(event.target.checked)}
                                />
                            }
                            label={localeMessages["embed_include_course_title"]}
                            sx={{ mb: 1, mt: '10px', ml: 0, mr: 0 }}
                        />
                    )}
                    {hasCourseImage && (
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={includeCourseImage}
                                    onChange={(event) => setIncludeCourseImage(event.target.checked)}
                                />
                            }
                            label={localeMessages["embed_include_course_image"]}
                            sx={{ mb: 1, mt: '10px', ml: 0, mr: 0 }}
                        />
                    )}
                    {hasLinkedNewsletter && (
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={includeNewsletterCheck}
                                    onChange={(event) => setIncludeNewsletterCheck(event.target.checked)}
                                />
                            }
                            label={localeMessages["embed_include_newsletter_check"]}
                            sx={{ mb: 1, mt: '10px', ml: 0, mr: 0 }}
                        />
                    )}
                    <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                        {localeMessages["embed_code_dialog_title"]}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {localeMessages["embed_code_dialog_description"]}
                    </Typography>
                    {embedSnippetLoading && (
                        <Box sx={{ py: 2 }}>
                            <LinearProgress />
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                {localeMessages["embed_code_loading"]}
                            </Typography>
                        </Box>
                    )}
                    {!embedSnippetLoading && embedSnippetError && (
                        <Alert severity="error">{localeMessages["embed_code_error"]}</Alert>
                    )}
                    {!embedSnippetLoading && !embedSnippetError && embedWidgetHtml && (
                        <>
                            <EmbedCodeBlock
                                label={localeMessages["embed_script_step_title"]}
                                code={embedScriptHtml}
                                copied={embedScriptCopied}
                                onCopy={handleCopyEmbedScript}
                                copyLabel={localeMessages["copy_embed_script"]}
                                copiedLabel={localeMessages["embed_code_copied"]}
                            />
                            <EmbedCodeBlock
                                label={localeMessages["embed_widget_step_title"]}
                                code={displayedEmbedWidgetHtml}
                                copied={embedWidgetCopied}
                                onCopy={handleCopyEmbedWidget}
                                copyLabel={localeMessages["copy_embed_widget"]}
                                copiedLabel={localeMessages["embed_code_copied"]}
                            />
                        </>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseEmbedDialog}>{localeMessages["close"]}</Button>
                </DialogActions>
            </Dialog>
        </Base>
    )
}

render({children: <Course />});

export default Course;
