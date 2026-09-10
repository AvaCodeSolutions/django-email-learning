import { useEffect, useState } from 'react';
import {
    Alert,
    Box,
    Chip,
    Grid,
    LinearProgress,
    Paper,
    Stack,
    Tooltip,
    Typography,
} from '@mui/material';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';

const formatPercent = (rate) => `${Math.round(rate * 100)}%`;

function SummaryTile({ label, value }) {
    return (
        <Grid size={{ xs: 6, sm: 3 }}>
            <Box sx={{ px: 2, py: 1.5, borderRadius: 2, backgroundColor: 'background.box' }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>{label}</Typography>
                <Typography variant="h6">{value}</Typography>
            </Box>
        </Grid>
    );
}

function AnswerRow({ answer, localeMessages, showRates }) {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.75 }}>
            <Box sx={{ width: 20, display: 'flex', justifyContent: 'center', flexShrink: 0 }}>
                {answer.is_correct && (
                    <CheckCircleOutlinedIcon fontSize="small" sx={{ color: 'success.main' }} />
                )}
            </Box>
            <Typography
                variant="body2"
                sx={{ flex: 1, minWidth: 0, fontWeight: answer.is_correct ? 600 : 400, wordBreak: 'break-word' }}
            >
                {answer.text}
            </Typography>
            {showRates && answer.selected_rate !== null && (
                <Box sx={{ width: { xs: 60, sm: 120 }, flexShrink: 0 }}>
                    <LinearProgress
                        variant="determinate"
                        value={Math.min(100, answer.selected_rate * 100)}
                        color={answer.is_correct ? 'success' : 'primary'}
                        sx={{ height: 6, borderRadius: 3 }}
                    />
                </Box>
            )}
            <Typography variant="caption" sx={{ color: 'text.secondary', flexShrink: 0, minWidth: 76, textAlign: 'end' }}>
                {showRates && answer.selected_rate !== null
                    ? `${formatPercent(answer.selected_rate)} (${answer.selected_count})`
                    : `${localeMessages['quiz_analytics_chose']}: ${answer.selected_count}`}
            </Typography>
        </Box>
    );
}

function QuestionCard({ question, localeMessages, minResponses }) {
    // Rates come back as null from the API whenever the sample is under the threshold, so
    // the component never has to decide on its own whether a percentage is safe to show.
    const showRates = question.correct_rate !== null;

    return (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start', mb: 1 }}>
                <Typography variant="subtitle1" sx={{ flex: 1, minWidth: 0, wordBreak: 'break-word' }}>
                    {question.text}
                </Typography>
                {question.is_multiple_choice && (
                    <Chip size="small" variant="outlined" label={localeMessages['quiz_analytics_multiple_choice']} />
                )}
            </Stack>

            {question.asked_count === 0 ? (
                <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>
                    {localeMessages['quiz_analytics_not_asked']}
                </Typography>
            ) : (
                <Stack
                    direction="row"
                    spacing={2}
                    sx={{ flexWrap: 'wrap', rowGap: 0.5, mb: 1, color: 'text.secondary' }}
                >
                    <Typography variant="caption">
                        {`${localeMessages['quiz_analytics_asked']}: ${question.asked_count}`}
                    </Typography>
                    <Typography variant="caption">
                        {`${localeMessages['quiz_analytics_answered']}: ${question.answered_count}`}
                    </Typography>
                    <Typography variant="caption">
                        {`${localeMessages['quiz_analytics_skipped']}: ${question.skipped_count}`}
                    </Typography>
                    <Typography variant="caption">
                        {showRates
                            ? `${localeMessages['quiz_analytics_correct_rate']}: ${formatPercent(question.correct_rate)} (${question.correct_count}/${question.asked_count})`
                            : `${localeMessages['quiz_analytics_correct']}: ${question.correct_count}/${question.asked_count}`}
                    </Typography>
                </Stack>
            )}

            {question.asked_count > 0 && !showRates && (
                <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mb: 1 }}>
                    {(localeMessages['quiz_analytics_low_sample'] || '').replace('MIN_RESPONSES', minResponses)}
                </Typography>
            )}

            <Box>
                {question.answers.map((answer) => (
                    <AnswerRow
                        key={answer.id}
                        answer={answer}
                        localeMessages={localeMessages}
                        showRates={showRates}
                    />
                ))}
            </Box>
        </Paper>
    );
}

function QuizAnalytics({ quizId }) {
    const { apiBaseUrl: rawApiBaseUrl, localeMessages } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');

    const [analytics, setAnalytics] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState('');

    useEffect(() => {
        let cancelled = false;
        setIsLoading(true);
        setErrorMessage('');
        apiClient
            .get(`${apiBaseUrl}/organizations/${organizationId}/quizzes/${quizId}/analytics/`)
            .then((data) => {
                if (!cancelled) {
                    setAnalytics(data);
                }
            })
            .catch((error) => {
                console.error('Error loading quiz analytics:', error);
                if (!cancelled) {
                    setErrorMessage(localeMessages['quiz_analytics_load_failed']);
                }
            })
            .finally(() => {
                if (!cancelled) {
                    setIsLoading(false);
                }
            });
        return () => {
            cancelled = true;
        };
    }, [apiBaseUrl, organizationId, quizId, localeMessages]);

    if (isLoading) {
        return <Box sx={{ py: 3 }}><LinearProgress /></Box>;
    }

    if (errorMessage) {
        return <Alert severity="error" sx={{ my: 2 }}>{errorMessage}</Alert>;
    }

    if (!analytics) {
        return null;
    }

    if (analytics.total_submissions === 0) {
        return (
            <Alert severity="info" icon={<InfoOutlinedIcon fontSize="inherit" />} sx={{ my: 2 }}>
                {localeMessages['quiz_analytics_no_data']}
            </Alert>
        );
    }

    const sharedCourses = (analytics.shared_with || []).map((content) => content.course_title);
    const isShared = (analytics.shared_with || []).length > 1;

    return (
        <Box sx={{ py: 1 }}>
            {isShared && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                    {(localeMessages['quiz_analytics_shared_warning'] || '')
                        .replace('SHARED_COURSES', [...new Set(sharedCourses)].join(', '))}
                </Alert>
            )}

            <Grid container spacing={2} sx={{ mb: 2 }}>
                <SummaryTile
                    label={localeMessages['quiz_analytics_counted']}
                    value={analytics.counted_submissions}
                />
                <SummaryTile
                    label={localeMessages['quiz_analytics_total_submissions']}
                    value={analytics.total_submissions}
                />
                <SummaryTile
                    label={localeMessages['quiz_analytics_repeat_attempts']}
                    value={analytics.repeat_attempts}
                />
            </Grid>

            <Stack direction="row" spacing={0.5} sx={{ alignItems: 'flex-start', mb: 1 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {localeMessages['quiz_analytics_basis']}
                </Typography>
                <Tooltip title={localeMessages['quiz_analytics_correct_definition']} placement="top">
                    <InfoOutlinedIcon fontSize="small" sx={{ color: 'text.secondary', flexShrink: 0 }} />
                </Tooltip>
            </Stack>

            {analytics.legacy_submissions > 0 && (
                <Alert severity="info" sx={{ mb: 2 }}>
                    {(localeMessages['quiz_analytics_legacy_note'] || '')
                        .replace('LEGACY_COUNT', analytics.legacy_submissions)}
                </Alert>
            )}

            {analytics.counted_submissions === 0 ? (
                <Alert severity="info" sx={{ my: 2 }}>
                    {localeMessages['quiz_analytics_no_data']}
                </Alert>
            ) : (
                analytics.questions.map((question) => (
                    <QuestionCard
                        key={question.id}
                        question={question}
                        localeMessages={localeMessages}
                        minResponses={analytics.min_responses_for_rates}
                    />
                ))
            )}
        </Box>
    );
}

export default QuizAnalytics;
