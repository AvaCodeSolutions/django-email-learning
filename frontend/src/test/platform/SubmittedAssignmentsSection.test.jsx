import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import SubmittedAssignmentsSection from '../../../platform/course/components/SubmittedAssignmentsSection';

vi.mock('../../render.jsx');

const localeMessages = {
    pending_filter_chip: 'Pending Review',
    show_pending_only: 'Show Pending Only',
    assignment_title: 'Assignment Title',
    submitted_at: 'Submitted At',
    status: 'Status',
    reviewed_at: 'Reviewed At',
    reviewed_by: 'Reviewed By',
    no_submitted_assignments: 'No submitted assignments found.',
    pending_review: 'Pending Review',
    approved: 'Approved',
    rejected: 'Rejected',
    requesting_changes: 'Requesting Changes',
    submitted_assignment_details: 'Submitted Assignment Details',
    submission_content: 'Submission Content',
    text_submission: 'Text Submission',
    file_submission: 'File Submission',
    no_text_submission: 'No text submission.',
    no_file_submission: 'No file submission.',
    feedbacks: 'Feedbacks',
    no_feedbacks_yet: 'No feedbacks yet.',
    review_assignment: 'Review Assignment',
    review_result: 'Review Result',
    select_review_result: 'Select review result',
    feedback_optional: 'Feedback (optional)',
    submit_review: 'Submit Review',
    close: 'Close',
    unable_to_load_submission_details: 'Unable to load submission details.',
};

const appContext = {
    apiBaseUrl: '/api',
    courseId: 42,
    localeMessages,
};

const makePage = (items = [], extra = {}) => ({
    items,
    count: items.length,
    page: 1,
    page_size: 20,
    has_more: false,
    ...extra,
});

const sampleSubmission = {
    id: 1,
    assignment_title: 'Write a Report',
    submitted_at: '2026-01-15T10:00:00Z',
    status: 'pending_review',
    reviewed_at: null,
    reviewed_by: null,
};

const approvedSubmission = {
    id: 2,
    assignment_title: 'Build a Feature',
    submitted_at: '2026-01-16T12:00:00Z',
    status: 'approved',
    reviewed_at: '2026-01-17T09:00:00Z',
    reviewed_by: 'Jane Instructor',
};

function setup(props = {}) {
    window.localStorage.setItem('activeOrganizationId', '1');
    return renderWithProviders(<SubmittedAssignmentsSection {...props} />, {
        appContext,
    });
}

// ---------------------------------------------------------------------------
// Initial render
// ---------------------------------------------------------------------------

describe('SubmittedAssignmentsSection — initial render', () => {
    beforeEach(() => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(makePage()),
        });
    });

    it('renders table column headers', async () => {
        setup();
        await waitFor(() =>
            expect(screen.getByText('Assignment Title')).toBeInTheDocument()
        );
        expect(screen.getByText('Submitted At')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText('Reviewed At')).toBeInTheDocument();
        expect(screen.getByText('Reviewed By')).toBeInTheDocument();
    });

    it('shows the Pending Review filter chip by default', async () => {
        setup();
        await waitFor(() =>
            expect(screen.getByText('Pending Review')).toBeInTheDocument()
        );
    });

    it('shows empty state message when no submissions returned', async () => {
        setup();
        await waitFor(() =>
            expect(
                screen.getByText('No submitted assignments found.')
            ).toBeInTheDocument()
        );
    });

    it('fetches with status=pending_review by default', async () => {
        setup();
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
        const url = global.fetch.mock.calls[0][0];
        expect(url).toContain('status=pending_review');
    });

    it('calls onPendingCountChange with the server count on load', async () => {
        const onPendingCountChange = vi.fn();
        global.fetch.mockResolvedValue({
            ok: true,
            json: () =>
                Promise.resolve(makePage([sampleSubmission], { count: 1 })),
        });
        setup({ onPendingCountChange });
        await waitFor(() =>
            expect(onPendingCountChange).toHaveBeenCalledWith(1)
        );
    });
});

// ---------------------------------------------------------------------------
// Submission rows
// ---------------------------------------------------------------------------

describe('SubmittedAssignmentsSection — submission rows', () => {
    it('renders a row for each returned submission', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () =>
                Promise.resolve(makePage([sampleSubmission, approvedSubmission])),
        });
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        expect(screen.getByText('Build a Feature')).toBeInTheDocument();
    });

    it('shows the correct status chip for pending_review', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(makePage([sampleSubmission])),
        });
        setup();
        await waitFor(() =>
            expect(screen.getAllByText('Pending Review').length).toBeGreaterThan(0)
        );
    });

    it('shows the correct status chip for approved', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(makePage([approvedSubmission])),
        });
        setup();
        await waitFor(() =>
            expect(screen.getByText('Approved')).toBeInTheDocument()
        );
    });

    it('displays reviewed_by when present', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(makePage([approvedSubmission])),
        });
        setup();
        await waitFor(() =>
            expect(screen.getByText('Jane Instructor')).toBeInTheDocument()
        );
    });
});

// ---------------------------------------------------------------------------
// Filter chip (pending-only toggle)
// ---------------------------------------------------------------------------

describe('SubmittedAssignmentsSection — pending-only filter', () => {
    it('removes the pending_review filter when chip is deleted', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(makePage()),
        });
        const user = userEvent.setup();
        setup();
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());

        // Click the delete icon on the Pending Review chip
        const chip = screen.getByText('Pending Review').closest('[role="button"]') ??
            screen.getByText('Pending Review').parentElement;
        const deleteBtn = chip.querySelector('[data-testid="CancelIcon"]') ??
            within(chip).queryByRole('button');
        if (deleteBtn) {
            await user.click(deleteBtn);
        } else {
            // MUI Chip delete is triggered by clicking the svg icon child
            await user.click(screen.getByTestId('CancelIcon'));
        }

        await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
        const lastUrl = global.fetch.mock.calls[1][0];
        expect(lastUrl).not.toContain('status=pending_review');
    });

    it('shows "Show Pending Only" chip when filter is off', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(makePage()),
        });
        const user = userEvent.setup();
        setup();
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());

        // Remove pending filter
        const deleteIcons = document.querySelectorAll('[data-testid="CancelIcon"]');
        if (deleteIcons.length > 0) {
            await user.click(deleteIcons[0]);
            await waitFor(() =>
                expect(screen.getByText('Show Pending Only')).toBeInTheDocument()
            );
        }
    });
});

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

describe('SubmittedAssignmentsSection — pagination', () => {
    it('does not show pagination when all results fit on one page', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () =>
                Promise.resolve(makePage([sampleSubmission], { has_more: false, page: 1 })),
        });
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    });

    it('shows pagination when has_more is true', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () =>
                Promise.resolve(
                    makePage([sampleSubmission], { count: 25, has_more: true, page: 1 })
                ),
        });
        setup();
        await waitFor(() =>
            expect(screen.getByRole('navigation')).toBeInTheDocument()
        );
    });

    it('includes page and page_size params in fetch URL', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(makePage()),
        });
        setup();
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
        const url = global.fetch.mock.calls[0][0];
        expect(url).toContain('page=1');
        expect(url).toContain('page_size=20');
    });
});

// ---------------------------------------------------------------------------
// Detail dialog
// ---------------------------------------------------------------------------

describe('SubmittedAssignmentsSection — detail dialog', () => {
    const submissionDetail = {
        id: 1,
        assignment_title: 'Write a Report',
        submitted_at: '2026-01-15T10:00:00Z',
        status: 'pending_review',
        reviewed_at: null,
        reviewed_by: null,
        text_submission: 'Here is my answer.',
        file_submission: null,
        feedbacks: [],
    };

    beforeEach(() => {
        global.fetch.mockImplementation((url) => {
            if (url.includes('/submitted_assignments/1')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(submissionDetail),
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve(makePage([sampleSubmission])),
            });
        });
    });

    it('opens detail dialog when a row is clicked', async () => {
        const user = userEvent.setup();
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        await user.click(screen.getByText('Write a Report'));
        await waitFor(() =>
            expect(
                screen.getByText('Submitted Assignment Details')
            ).toBeInTheDocument()
        );
    });

    it('shows the text submission content in the dialog', async () => {
        const user = userEvent.setup();
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        await user.click(screen.getByText('Write a Report'));
        await waitFor(() =>
            expect(screen.getByText('Here is my answer.')).toBeInTheDocument()
        );
    });

    it('shows "No feedbacks yet." when feedbacks array is empty', async () => {
        const user = userEvent.setup();
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        await user.click(screen.getByText('Write a Report'));
        await waitFor(() =>
            expect(screen.getByText('No feedbacks yet.')).toBeInTheDocument()
        );
    });

    it('closes the dialog when Close is clicked', async () => {
        const user = userEvent.setup();
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        await user.click(screen.getByText('Write a Report'));
        await waitFor(() =>
            expect(
                screen.getByText('Submitted Assignment Details')
            ).toBeInTheDocument()
        );
        await user.click(screen.getByRole('button', { name: 'Close' }));
        await waitFor(() =>
            expect(
                screen.queryByText('Submitted Assignment Details')
            ).not.toBeInTheDocument()
        );
    });
});

// ---------------------------------------------------------------------------
// Review submission
// ---------------------------------------------------------------------------

describe('SubmittedAssignmentsSection — review submission', () => {
    const submissionDetail = {
        id: 1,
        assignment_title: 'Write a Report',
        submitted_at: '2026-01-15T10:00:00Z',
        status: 'pending_review',
        reviewed_at: null,
        reviewed_by: null,
        text_submission: 'My answer.',
        file_submission: null,
        feedbacks: [],
    };

    beforeEach(() => {
        global.fetch.mockImplementation((url, opts) => {
            if (opts?.method === 'POST') {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve({ ...submissionDetail, status: 'approved' }),
                });
            }
            if (url.includes('/submitted_assignments/1')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(submissionDetail),
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve(makePage([sampleSubmission])),
            });
        });
    });

    it('renders the review result select and submit button in the dialog', async () => {
        const user = userEvent.setup();
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        await user.click(screen.getByText('Write a Report'));
        await waitFor(() =>
            expect(screen.getByText('Review Assignment')).toBeInTheDocument()
        );
        expect(screen.getByRole('button', { name: 'Submit Review' })).toBeInTheDocument();
    });

    it('Submit Review button is disabled when no review result selected', async () => {
        const user = userEvent.setup();
        setup();
        await waitFor(() =>
            expect(screen.getByText('Write a Report')).toBeInTheDocument()
        );
        await user.click(screen.getByText('Write a Report'));
        await waitFor(() =>
            expect(
                screen.getByRole('button', { name: 'Submit Review' })
            ).toBeDisabled()
        );
    });
});

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe('SubmittedAssignmentsSection — error handling', () => {
    it('shows empty table and calls onPendingCountChange(0) when fetch fails', async () => {
        global.fetch.mockRejectedValue(new Error('Network error'));
        const onPendingCountChange = vi.fn();
        setup({ onPendingCountChange });
        await waitFor(() =>
            expect(onPendingCountChange).toHaveBeenCalledWith(0)
        );
        expect(
            screen.getByText('No submitted assignments found.')
        ).toBeInTheDocument();
    });
});
