import { useEffect, useState } from 'react';
import {
    Avatar,
    Alert,
    Box,
    Button,
    Chip,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Divider,
    LinearProgress,
    MenuItem,
    Pagination,
    Paper,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    Typography,
} from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined';
import CancelOutlinedIcon from '@mui/icons-material/CancelOutlined';
import PendingActionsOutlinedIcon from '@mui/icons-material/PendingActionsOutlined';
import AutorenewOutlinedIcon from '@mui/icons-material/AutorenewOutlined';
import AssignmentTurnedInOutlinedIcon from '@mui/icons-material/AssignmentTurnedInOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import FeedbackOutlinedIcon from '@mui/icons-material/FeedbackOutlined';
import RateReviewOutlinedIcon from '@mui/icons-material/RateReviewOutlined';
import PersonOutlineOutlinedIcon from '@mui/icons-material/PersonOutlineOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import AttachFileOutlinedIcon from '@mui/icons-material/AttachFileOutlined';
import OpenInNewOutlinedIcon from '@mui/icons-material/OpenInNewOutlined';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl, sanitizeImageUrl, sanitizeUrl } from '../../../src/sanitizeUrl.js';

function SubmittedAssignmentsSection({ onPendingCountChange }) {
    const { apiBaseUrl: rawApiBaseUrl, courseId, localeMessages } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');

    const pageSize = 20;
    const [submittedAssignments, setSubmittedAssignments] = useState([]);
    const [isSubmittedAssignmentsLoading, setIsSubmittedAssignmentsLoading] =
        useState(false);
    const [submittedAssignmentsPendingOnly, setSubmittedAssignmentsPendingOnly] =
        useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalCount, setTotalCount] = useState(0);
    const [showPagination, setShowPagination] = useState(false);
    const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
    const [isSubmissionDetailLoading, setIsSubmissionDetailLoading] = useState(false);
    const [submissionDetail, setSubmissionDetail] = useState(null);
    const [reviewResult, setReviewResult] = useState('');
    const [reviewFeedback, setReviewFeedback] = useState('');
    const [isReviewSubmitting, setIsReviewSubmitting] = useState(false);
    const [reviewError, setReviewError] = useState('');
    const [reviewSuccess, setReviewSuccess] = useState('');
    const reviewResultOptions = ['approved', 'rejected', 'requesting_changes'];

    const fetchSubmittedAssignments = () => {
        const params = new URLSearchParams();
        if (submittedAssignmentsPendingOnly) {
            params.set('status', 'pending_review');
        }
        params.set('page', currentPage);
        params.set('page_size', pageSize);
        const endpoint = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/submitted_assignments/?${params.toString()}`;

        setIsSubmittedAssignmentsLoading(true);
        return apiClient.get(endpoint)
            .then((data) => {
                const submissions = data.items || [];
                setSubmittedAssignments(submissions);
                setTotalCount(data.count || 0);
                setShowPagination(data.page !== 1 || data.has_more);
                if (onPendingCountChange) {
                    const pendingCount = submittedAssignmentsPendingOnly
                        ? data.count || 0
                        : submissions.filter(
                              (item) => item.status === 'pending_review'
                          ).length;
                    onPendingCountChange(pendingCount);
                }
            })
            .catch((error) => {
                console.error('Error fetching submitted assignments:', error);
                setSubmittedAssignments([]);
                setTotalCount(0);
                setShowPagination(false);
                if (onPendingCountChange) {
                    onPendingCountChange(0);
                }
            })
            .finally(() => setIsSubmittedAssignmentsLoading(false));
    };

    useEffect(() => {
        setCurrentPage(1);
    }, [submittedAssignmentsPendingOnly]);

    useEffect(() => {
        fetchSubmittedAssignments();
    }, [submittedAssignmentsPendingOnly, currentPage, apiBaseUrl, organizationId, courseId, onPendingCountChange]);

    const mapSubmissionStatusLabel = (status) => {
        if (status === 'pending_review') {
            return localeMessages['pending_review'] || 'Pending Review';
        }
        if (status === 'approved') {
            return localeMessages['approved'] || 'Approved';
        }
        if (status === 'rejected') {
            return localeMessages['rejected'] || 'Rejected';
        }
        if (status === 'requesting_changes') {
            return localeMessages['requesting_changes'] || 'Requesting Changes';
        }
        return status;
    };

    const getSubmissionStatusMeta = (status) => {
        if (status === 'approved') {
            return {
                label: mapSubmissionStatusLabel(status),
                color: 'success',
                icon: <CheckCircleOutlineIcon fontSize="small" />,
            };
        }
        if (status === 'rejected') {
            return {
                label: mapSubmissionStatusLabel(status),
                color: 'error',
                icon: <CancelOutlinedIcon fontSize="small" />,
            };
        }
        if (status === 'requesting_changes') {
            return {
                label: mapSubmissionStatusLabel(status),
                color: 'warning',
                icon: <AutorenewOutlinedIcon fontSize="small" />,
            };
        }
        return {
            label: mapSubmissionStatusLabel(status),
            color: 'default',
            icon: <PendingActionsOutlinedIcon fontSize="small" />,
        };
    };

    const renderStatusChip = (status) => {
        const meta = getSubmissionStatusMeta(status);
        return (
            <Chip
                icon={meta.icon}
                size="small"
                color={meta.color}
                label={meta.label}
                sx={{ fontWeight: 600 }}
            />
        );
    };

    const renderReviewResultValue = (value) => {
        if (!reviewResultOptions.includes(value)) {
            return localeMessages['select_review_result'] || 'Select review result';
        }

        if (value === 'approved') {
            return (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, lineHeight: 1.2 }}>
                    <CheckCircleOutlineIcon color="success" fontSize="small" />
                    <span>{localeMessages['approved'] || 'Approved'}</span>
                </Box>
            );
        }

        if (value === 'rejected') {
            return (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, lineHeight: 1.2 }}>
                    <CancelOutlinedIcon color="error" fontSize="small" />
                    <span>{localeMessages['rejected'] || 'Rejected'}</span>
                </Box>
            );
        }

        return (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, lineHeight: 1.2 }}>
                <AutorenewOutlinedIcon color="warning" fontSize="small" />
                <span>{localeMessages['requesting_changes'] || 'Requesting Changes'}</span>
            </Box>
        );
    };

    const formatDateTime = (value) => {
        if (!value) {
            return '-';
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleString();
    };

    const getFileNameFromUrl = (url) => {
        if (!url) {
            return '-';
        }
        try {
            const pathname = new URL(url, window.location.origin).pathname;
            const encodedName = pathname.split('/').filter(Boolean).pop();
            if (!encodedName) {
                return 'Attached file';
            }
            return decodeURIComponent(encodedName);
        } catch {
            const cleanUrl = url.split('?')[0].split('#')[0];
            const fallbackName = cleanUrl.split('/').filter(Boolean).pop();
            return fallbackName || 'Attached file';
        }
    };

    const openSubmissionDetail = (submissionId) => {
        const endpoint = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/submitted_assignments/${submissionId}`;
        setIsDetailDialogOpen(true);
        setIsSubmissionDetailLoading(true);
        setSubmissionDetail(null);
        setReviewError('');
        setReviewSuccess('');
        setReviewFeedback('');
        setReviewResult('');

        apiClient.get(endpoint)
            .then((data) => {
                setSubmissionDetail(data);
                setReviewResult(
                    reviewResultOptions.includes(data.status) ? data.status : ''
                );
            })
            .catch((error) => {
                console.error('Error fetching submission detail:', error);
            })
            .finally(() => setIsSubmissionDetailLoading(false));
    };

    const submitReview = () => {
        if (!submissionDetail?.id) {
            return;
        }
        if (!reviewResultOptions.includes(reviewResult)) {
            setReviewError(
                localeMessages['review_result_required'] ||
                    'Please select a review result.'
            );
            return;
        }
        const endpoint = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/submitted_assignments/${submissionDetail.id}/review/`;
        setIsReviewSubmitting(true);
        setReviewError('');
        setReviewSuccess('');

        apiClient.post(endpoint, {
                review_result: reviewResult,
                comment: reviewFeedback.trim() || null,
        })
            .then((data) => {
                setSubmissionDetail(data);
                setReviewSuccess(
                    localeMessages['review_submitted_success'] ||
                        'Review submitted successfully.'
                );
                return fetchSubmittedAssignments().then(() => {
                    setTimeout(() => setIsDetailDialogOpen(false), 500);
                });
            })
            .catch((error) => {
                setReviewError(
                    error.message ||
                        localeMessages['review_submit_failed'] ||
                        'Failed to submit review.'
                );
            })
            .finally(() => setIsReviewSubmitting(false));
    };

    return (
        <>
            <Stack direction="row" spacing={1} sx={{ px: 1,mb: 2, flexWrap: 'wrap' }}>
                {submittedAssignmentsPendingOnly ? (
                    <Chip
                        color="primary"
                        label={localeMessages['pending_filter_chip'] || 'Pending Review'}
                        onDelete={() => setSubmittedAssignmentsPendingOnly(false)}
                    />
                ) : (
                    <Chip
                        variant="outlined"
                        label={localeMessages['show_pending_only'] || 'Show Pending Only'}
                        onClick={() => setSubmittedAssignmentsPendingOnly(true)}
                    />
                )}
            </Stack>

            {isSubmittedAssignmentsLoading ? (
                <LinearProgress />
            ) : (
                <TableContainer component={Paper} sx={{ borderRadius: { xs: 0, md: '8px' }, border: 'none', boxShadow: 'none' }}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>
                                    {localeMessages['assignment_title'] || 'Assignment Title'}
                                </TableCell>
                                <TableCell>
                                    {localeMessages['submitted_at'] || 'Submitted At'}
                                </TableCell>
                                <TableCell>{localeMessages['status'] || 'Status'}</TableCell>
                                <TableCell>
                                    {localeMessages['reviewed_at'] || 'Reviewed At'}
                                </TableCell>
                                <TableCell>
                                    {localeMessages['reviewed_by'] || 'Reviewed By'}
                                </TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {submittedAssignments.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} align="center">
                                        <Typography
                                            variant="body2"
                                            sx={{ color: 'text.secondary' }}
                                        >
                                            {localeMessages['no_submitted_assignments'] ||
                                                'No submitted assignments found.'}
                                        </Typography>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                submittedAssignments.map((item) => (
                                    <TableRow
                                        key={item.id}
                                        hover
                                        onClick={() => openSubmissionDetail(item.id)}
                                        sx={{ cursor: 'pointer' }}
                                    >
                                        <TableCell>{item.assignment_title}</TableCell>
                                        <TableCell>
                                            {formatDateTime(item.submitted_at)}
                                        </TableCell>
                                        <TableCell>
                                            {renderStatusChip(item.status)}
                                        </TableCell>
                                        <TableCell>
                                            {formatDateTime(item.reviewed_at)}
                                        </TableCell>
                                        <TableCell>{item.reviewed_by || '-'}</TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}
            {showPagination && (
                <Pagination
                    sx={{ mt: 2 }}
                    count={Math.ceil(totalCount / pageSize)}
                    page={currentPage}
                    onChange={(_, page) => setCurrentPage(page)}
                />
            )}

            <Dialog
                open={isDetailDialogOpen}
                onClose={() => setIsDetailDialogOpen(false)}
                fullWidth
                maxWidth="md"
            >
                <DialogTitle>
                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                        <AssignmentTurnedInOutlinedIcon fontSize="small" />
                        <Typography variant="h6" component="span" sx={{ fontWeight: 700 }}>
                            {localeMessages['submitted_assignment_details'] || 'Submitted Assignment Details'}
                        </Typography>
                    </Stack>
                </DialogTitle>
                <DialogContent>
                    {isSubmissionDetailLoading ? (
                        <LinearProgress />
                    ) : submissionDetail ? (
                        <Stack spacing={2} sx={{ pt: 0.5 }}>
                            <Typography variant="h6" sx={{ fontWeight: 700 }}>
                                {submissionDetail.assignment_title}
                            </Typography>
                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack spacing={1.5}>
                                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                                        <InfoOutlinedIcon fontSize="small" color="action" />
                                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                                            {localeMessages['status'] || 'Status'}
                                        </Typography>
                                    </Stack>

                                    <Box
                                        sx={{
                                            p: 1.5,
                                            border: '1px solid',
                                            borderColor: 'divider',
                                            borderRadius: 1.25,
                                            backgroundColor: 'background.default',
                                        }}
                                    >
                                        <Stack spacing={1.25}>
                                            <Stack direction="row" spacing={1} useFlexGap sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                                                {renderStatusChip(submissionDetail.status)}
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    {localeMessages['submitted_at'] || 'Submitted At'}: {formatDateTime(submissionDetail.submitted_at)}
                                                </Typography>
                                            </Stack>
                                            <Stack direction="row" spacing={2} useFlexGap sx={{ pt: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    {localeMessages['reviewed_at'] || 'Reviewed At'}: {formatDateTime(submissionDetail.reviewed_at)}
                                                </Typography>
                                                <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                                                    {submissionDetail.reviewed_by?.photo ? (
                                                        <Avatar
                                                            src={sanitizeImageUrl(submissionDetail.reviewed_by.photo)}
                                                            alt={submissionDetail.reviewed_by.display_name || 'Reviewer'}
                                                            sx={{ width: 26, height: 26 }}
                                                        />
                                                    ) : null}
                                                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                        {localeMessages['reviewed_by'] || 'Reviewed By'}: {submissionDetail.reviewed_by?.display_name || '-'}
                                                    </Typography>
                                                </Stack>
                                            </Stack>
                                        </Stack>
                                    </Box>
                                </Stack>
                            </Paper>

                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack spacing={1.5}>
                                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                                        <PersonOutlineOutlinedIcon fontSize="small" color="action" />
                                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                                            {localeMessages['learner_information'] || 'Learner Information'}
                                        </Typography>
                                    </Stack>

                                    {submissionDetail.learner ? (
                                        <Box
                                            sx={{
                                                p: 1.5,
                                                border: '1px solid',
                                                borderColor: 'divider',
                                                borderRadius: 1.25,
                                                backgroundColor: 'background.default',
                                            }}
                                        >
                                            <Stack spacing={1.25}>
                                                <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center', flexWrap: 'nowrap' }}>
                                                    <Avatar
                                                        src={sanitizeImageUrl(submissionDetail.learner.photo)}
                                                        alt={submissionDetail.learner.email || 'Learner'}
                                                        sx={{ width: 36, height: 36 }}
                                                    >
                                                        {submissionDetail.learner.email?.charAt(0)?.toUpperCase() || 'L'}
                                                    </Avatar>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', minHeight: 36 }}>
                                                        <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                                                            {submissionDetail.learner.email || '-'}
                                                        </Typography>
                                                    </Box>
                                                </Stack>

                                                <Stack direction="row" spacing={2} useFlexGap sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                                                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                        {localeMessages['learner_id'] || 'Learner ID'}: {submissionDetail.learner.id ?? '-'}
                                                    </Typography>
                                                </Stack>
                                            </Stack>
                                        </Box>
                                    ) : (
                                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                            {localeMessages['learner_not_available'] || 'Learner information is not available.'}
                                        </Typography>
                                    )}
                                </Stack>
                            </Paper>

                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack spacing={1.25}>
                                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                                        <DescriptionOutlinedIcon fontSize="small" color="action" />
                                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                                            {localeMessages['submission_content'] || 'Submission Content'}
                                        </Typography>
                                    </Stack>
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                        {localeMessages['text_submission'] || 'Text Submission'}
                                    </Typography>
                                    {submissionDetail.text_submission ? (
                                        <Box
                                            sx={{
                                                p: 1.5,
                                                border: '1px solid',
                                                borderColor: 'divider',
                                                borderRadius: 1,
                                                backgroundColor: 'background.paper',
                                                whiteSpace: 'pre-wrap',
                                            }}
                                        >
                                            <Typography variant="body2">
                                                {submissionDetail.text_submission}
                                            </Typography>
                                        </Box>
                                    ) : (
                                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                            {localeMessages['no_text_submission'] || 'No text submission.'}
                                        </Typography>
                                    )}
                                    <Stack spacing={0.75} sx={{ pt: 0.5 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                            {localeMessages['file_submission'] || 'File Submission'}
                                        </Typography>
                                        {submissionDetail.file_submission ? (
                                            <Box
                                                sx={{
                                                    p: 1,
                                                    border: '1px solid',
                                                    borderColor: 'divider',
                                                    borderRadius: 1,
                                                    backgroundColor: 'background.paper',
                                                }}
                                            >
                                                <Stack
                                                    direction="row"
                                                    spacing={1}
                                                    useFlexGap
                                                    sx={{
                                                        alignItems: 'center',
                                                        justifyContent: 'space-between',
                                                        flexWrap: 'wrap',
                                                    }}
                                                >
                                                    <Stack direction="row" spacing={0.75} sx={{ minWidth: 0, alignItems: 'center' }}>
                                                        <AttachFileOutlinedIcon fontSize="small" color="action" />
                                                        <Typography
                                                            variant="body2"
                                                            sx={{
                                                                color: 'text.secondary',
                                                                wordBreak: 'break-all',
                                                            }}
                                                        >
                                                            {getFileNameFromUrl(submissionDetail.file_name)}
                                                        </Typography>
                                                    </Stack>
                                                    <Typography
                                                        component="a"
                                                        href={sanitizeUrl(submissionDetail.file_submission)}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        variant="body2"
                                                        sx={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            gap: 0.5,
                                                            color: 'primary.main',
                                                            fontWeight: 600,
                                                            textDecoration: 'none',
                                                        }}
                                                    >
                                                        {localeMessages['open_file'] || 'Open file'}
                                                        <OpenInNewOutlinedIcon fontSize="inherit" />
                                                    </Typography>
                                                </Stack>
                                            </Box>
                                        ) : (
                                            <Typography component="span" variant="body2" sx={{ color: 'text.secondary' }}>
                                                {localeMessages['no_file_submission'] || 'No file submission.'}
                                            </Typography>
                                        )}
                                    </Stack>
                                </Stack>
                            </Paper>

                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack direction="row" spacing={1} sx={{ mb: 1.5, alignItems: 'center' }}>
                                    <FeedbackOutlinedIcon fontSize="small" color="action" />
                                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                                        {localeMessages['feedbacks'] || 'Feedbacks'}
                                    </Typography>
                                </Stack>
                            {submissionDetail.feedbacks?.length ? (
                                submissionDetail.feedbacks.map((feedback, index) => (
                                    <Box
                                        key={`${feedback.provided_at}-${index}`}
                                        sx={{
                                            p: 1.5,
                                            border: '1px solid',
                                            borderColor: 'divider',
                                            borderRadius: 1,
                                            backgroundColor: 'background.default',
                                            mb: 1,
                                        }}
                                    >
                                        <Stack direction="row" spacing={1.25} sx={{ mt: 1, alignItems: 'center' }}>
                                            {feedback.provided_by?.photo ? (
                                                <Avatar
                                                    src={sanitizeImageUrl(feedback.provided_by.photo)}
                                                    alt={feedback.provided_by.display_name || 'Provider'}
                                                    sx={{ width: 24, height: 24 }}
                                                />
                                            ) : null}
                                            <Typography
                                                variant="caption"
                                                sx={{
                                                    color: 'text.secondary',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    minHeight: 24,
                                                    lineHeight: 1.2,
                                                }}
                                            >
                                                {(feedback.provided_by?.display_name || '-') + ' • ' + formatDateTime(feedback.provided_at)}
                                            </Typography>
                                        </Stack>
                                        <Typography variant="body2" sx={{ my: 1 }}>
                                            {feedback.comment}
                                        </Typography>

                                    </Box>
                                ))
                            ) : (
                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                    {localeMessages['no_feedbacks_yet'] || 'No feedbacks yet.'}
                                </Typography>
                            )}
                            </Paper>

                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack direction="row" spacing={1} sx={{ mb: 1.5, alignItems: 'center' }}>
                                    <RateReviewOutlinedIcon fontSize="small" color="action" />
                                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                                        {localeMessages['review_assignment'] || 'Review Assignment'}
                                    </Typography>
                                </Stack>
                            {reviewError ? <Alert severity="error">{reviewError}</Alert> : null}
                            {reviewSuccess ? <Alert severity="success">{reviewSuccess}</Alert> : null}
                            <TextField
                                select
                                fullWidth
                                size="small"
                                label={localeMessages['review_result'] || 'Review Result'}
                                value={reviewResult}
                                onChange={(e) => setReviewResult(e.target.value)}
                                sx={{ mt: 1 }}
                                slotProps={{
                                    select: {
                                        renderValue: renderReviewResultValue,
                                        sx: {
                                            '& .MuiSelect-select': {
                                                display: 'flex',
                                                alignItems: 'center',
                                            },
                                        },
                                    },
                                }}
                            >
                                <MenuItem value="" disabled>
                                    {localeMessages['select_review_result'] || 'Select review result'}
                                </MenuItem>
                                <MenuItem value="approved" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CheckCircleOutlineIcon color="success" fontSize="small" />
                                    {localeMessages['approved'] || 'Approved'}
                                </MenuItem>
                                <MenuItem value="rejected" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CancelOutlinedIcon color="error" fontSize="small" />
                                    {localeMessages['rejected'] || 'Rejected'}
                                </MenuItem>
                                <MenuItem value="requesting_changes" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <AutorenewOutlinedIcon color="warning" fontSize="small" />
                                    {localeMessages['requesting_changes'] || 'Requesting Changes'}
                                </MenuItem>
                            </TextField>
                            <TextField
                                fullWidth
                                multiline
                                minRows={3}
                                label={localeMessages['feedback_optional'] || 'Feedback (optional)'}
                                value={reviewFeedback}
                                onChange={(e) => setReviewFeedback(e.target.value)}
                                sx={{ mt: 1.5 }}
                            />
                            <Box sx={{ mt: 1.5 }}>
                                <Button
                                    variant="contained"
                                    onClick={submitReview}
                                    disabled={
                                        isReviewSubmitting ||
                                        !reviewResultOptions.includes(reviewResult)
                                    }
                                >
                                    {isReviewSubmitting
                                        ? localeMessages['submitting'] || 'Submitting...'
                                        : localeMessages['submit_review'] || 'Submit Review'}
                                </Button>
                            </Box>
                            </Paper>
                        </Stack>
                    ) : (
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                            {localeMessages['unable_to_load_submission_details'] || 'Unable to load submission details.'}
                        </Typography>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setIsDetailDialogOpen(false)}>
                        {localeMessages['close'] || 'Close'}
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
}

export default SubmittedAssignmentsSection;
