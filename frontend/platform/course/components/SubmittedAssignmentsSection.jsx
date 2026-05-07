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
import { useAppContext } from '../../../src/render.jsx';
import { getCookie } from '../../../src/utils.js';

function SubmittedAssignmentsSection({ onPendingCountChange }) {
    const { apiBaseUrl, courseId, localeMessages } = useAppContext();
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
        return fetch(endpoint, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
            .then((response) => response.json())
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

    const openSubmissionDetail = (submissionId) => {
        const endpoint = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/submitted_assignments/${submissionId}`;
        setIsDetailDialogOpen(true);
        setIsSubmissionDetailLoading(true);
        setSubmissionDetail(null);
        setReviewError('');
        setReviewSuccess('');
        setReviewFeedback('');
        setReviewResult('');

        fetch(endpoint, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
            .then((response) => response.json())
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
        const endpoint = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/submitted_assignment/${submissionDetail.id}/review/`;
        setIsReviewSubmitting(true);
        setReviewError('');
        setReviewSuccess('');

        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                review_result: reviewResult,
                comment: reviewFeedback.trim() || null,
            }),
        })
            .then(async (response) => {
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to submit review.');
                }
                return data;
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
            <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap' }}>
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
                <TableContainer component={Paper}>
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
                    <Stack direction="row" spacing={1} alignItems="center">
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
                                <Stack spacing={1.25}>
                                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                                        {localeMessages['status'] || 'Status'}
                                    </Typography>
                                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                                        {renderStatusChip(submissionDetail.status)}
                                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                            {localeMessages['submitted_at'] || 'Submitted At'}: {formatDateTime(submissionDetail.submitted_at)}
                                        </Typography>
                                    </Stack>
                                    <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                            {localeMessages['reviewed_at'] || 'Reviewed At'}: {formatDateTime(submissionDetail.reviewed_at)}
                                        </Typography>
                                        <Stack direction="row" spacing={1} alignItems="center">
                                            {submissionDetail.reviewed_by?.photo ? (
                                                <Avatar
                                                    src={submissionDetail.reviewed_by.photo}
                                                    alt={submissionDetail.reviewed_by.display_name || 'Reviewer'}
                                                    sx={{ width: 28, height: 28 }}
                                                />
                                            ) : null}
                                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                {localeMessages['reviewed_by'] || 'Reviewed By'}: {submissionDetail.reviewed_by?.display_name || '-'}
                                            </Typography>
                                        </Stack>
                                    </Stack>
                                </Stack>
                            </Paper>

                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack spacing={1.25}>
                                    <Stack direction="row" spacing={1} alignItems="center">
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
                                    <Stack direction="row" spacing={1} alignItems="center" sx={{ pt: 0.5 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                            {localeMessages['file_submission'] || 'File Submission'}:
                                        </Typography>
                                        {submissionDetail.file_submission ? (
                                            <Typography
                                                component="a"
                                                href={submissionDetail.file_submission}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                variant="body2"
                                                sx={{ color: 'primary.main', textDecoration: 'underline' }}
                                            >
                                                {localeMessages['open_file'] || 'Open file'}
                                            </Typography>
                                        ) : (
                                            <Typography component="span" variant="body2" sx={{ color: 'text.secondary' }}>
                                                {localeMessages['no_file_submission'] || 'No file submission.'}
                                            </Typography>
                                        )}
                                    </Stack>
                                </Stack>
                            </Paper>

                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
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
                                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                                            {feedback.comment}
                                        </Typography>
                                        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
                                            {feedback.provided_by?.photo ? (
                                                <Avatar
                                                    src={feedback.provided_by.photo}
                                                    alt={feedback.provided_by.display_name || 'Provider'}
                                                    sx={{ width: 24, height: 24 }}
                                                />
                                            ) : null}
                                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                                {(feedback.provided_by?.display_name || '-') + ' • ' + formatDateTime(feedback.provided_at)}
                                            </Typography>
                                        </Stack>
                                    </Box>
                                ))
                            ) : (
                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                    {localeMessages['no_feedbacks_yet'] || 'No feedbacks yet.'}
                                </Typography>
                            )}
                            </Paper>

                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
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
                            >
                                <MenuItem value="" disabled>
                                    {localeMessages['select_review_result'] || 'Select review result'}
                                </MenuItem>
                                <MenuItem value="approved" sx={{ gap: 1 }}>
                                    <CheckCircleOutlineIcon color="success" fontSize="small" />
                                    {localeMessages['approved'] || 'Approved'}
                                </MenuItem>
                                <MenuItem value="rejected" sx={{ gap: 1 }}>
                                    <CancelOutlinedIcon color="error" fontSize="small" />
                                    {localeMessages['rejected'] || 'Rejected'}
                                </MenuItem>
                                <MenuItem value="requesting_changes" sx={{ gap: 1 }}>
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
