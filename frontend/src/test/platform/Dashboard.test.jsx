import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import Dashboard from '../../../platform/dashboard/Dashboard';

vi.mock('../../render.jsx');

vi.mock('@mui/material', async () => ({
  ...(await vi.importActual('@mui/material')),
  useMediaQuery: vi.fn(() => true),
}));

const localeMessages = {
  dashboard: 'Dashboard',
  welcome_back: 'Welcome back',
  welcome_back_name: 'Welcome back, NAME',
  dashboard_subtitle: "Here's what's happening at ORGANIZATION_NAME.",
  setup_checklist_title: 'Finish setting up your organization',
  setup_progress: 'DONE of TOTAL done',
  setup_course_title: 'Create your first course',
  setup_course_description: 'Publish a course so learners can start enrolling.',
  setup_course_cta: 'Create course',
  setup_team_title: 'Invite your team',
  setup_team_description: 'Add instructors or co-admins to help manage courses and learners.',
  setup_team_cta: 'Invite people',
  setup_profile_title: 'Complete your organization profile',
  setup_profile_description: 'Add a logo and social links so learners recognize you.',
  setup_profile_cta: 'Edit profile',
  setup_newsletter_title: 'Set up your newsletter',
  setup_newsletter_description: 'Send progress updates and announcements to enrolled learners.',
  setup_newsletter_cta: 'Set up',
  overview_title: 'Overview',
  stat_active_courses: 'Active courses',
  stat_enrolled_learners: 'Enrolled learners',
  stat_newsletter_subscribers: 'Newsletter subscribers',
  stat_content_delivery_health: 'Content delivery health',
  content_delivery_healthy: 'Steady',
  content_delivery_warning: 'Needs attention',
  content_delivery_critical: 'Not running',
  quick_actions_title: 'Quick actions',
  action_add_course_title: 'Add a course',
  action_add_course_description: 'Start a new course from scratch or duplicate an existing one.',
  action_add_course_cta: 'Create course',
  action_write_newsletter_title: 'Write a newsletter',
  action_write_newsletter_description: 'Draft an update to send to your subscribed learners.',
  action_write_newsletter_cta: 'Open newsletter',
  action_view_analytics_title: 'View analytics',
  action_view_analytics_description: 'See enrollment and engagement trends across your courses.',
  action_view_analytics_cta: 'Open analytics',
};

function setupFetch(jobHealth = 'healthy') {
  global.fetch.mockImplementation((url) => {
    if (url.includes('/status/jobs/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ jobs: { deliver_contents: { job_health_status: jobHealth } } }),
      });
    }
    if (url.includes('/organizations/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ organizations: [{ id: '1', name: 'Acme' }] }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

describe('Dashboard', () => {
  beforeEach(() => {
    setupFetch();
  });

  it('greets the user by name when a display name is available', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: { localeMessages, greetingName: 'Priya', availableFeatures: [] },
    });
    await waitFor(() => expect(screen.getByText('Welcome back, Priya')).toBeInTheDocument());
  });

  it('falls back to a generic greeting when no display name is available', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: { localeMessages, greetingName: null, availableFeatures: [] },
    });
    await waitFor(() => expect(screen.getByText('Welcome back')).toBeInTheDocument());
  });

  it('shows the setup checklist with incomplete items and hides the newsletter step when the feature is off', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSetup: { hasCourse: false, hasTeam: false, profileComplete: false, newsletterConfigured: false },
      },
    });
    await waitFor(() => expect(screen.getByText('0 of 3 done')).toBeInTheDocument());
    expect(screen.getByText('Create your first course')).toBeInTheDocument();
    expect(screen.queryByText('Set up your newsletter')).not.toBeInTheDocument();
  });

  it('includes the newsletter step in the checklist when the org can create a newsletter', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: ['newsletters', 'create_newsletter'],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: false },
      },
    });
    await waitFor(() => expect(screen.getByText('3 of 4 done')).toBeInTheDocument());
    expect(screen.getByText('Set up your newsletter')).toBeInTheDocument();
  });

  it('hides the newsletter step and quick action when newsletters are viewable but the org cannot create one', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: ['newsletters'],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: false },
        dashboardStats: { activeCourses: 1, enrolledLearners: 1, newsletterSubscribers: 4 },
      },
    });
    await waitFor(() => expect(screen.getByText('Add a course')).toBeInTheDocument());
    expect(screen.queryByText('Set up your newsletter')).not.toBeInTheDocument();
    expect(screen.queryByText('Write a newsletter')).not.toBeInTheDocument();
    // Viewing existing subscriber counts is a separate concern from being able to create a newsletter.
    expect(screen.getByText('Newsletter subscribers')).toBeInTheDocument();
  });

  it('hides the checklist entirely once every applicable step is done', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: ['newsletters', 'create_newsletter'],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: true },
        dashboardStats: { activeCourses: 1, enrolledLearners: 1, newsletterSubscribers: 1 },
      },
    });
    await waitFor(() => expect(screen.getByText('Add a course')).toBeInTheDocument());
    expect(screen.queryByText('Finish setting up your organization')).not.toBeInTheDocument();
  });

  it('hides the overview section entirely when there are no active courses or subscribers', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: ['newsletters'],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: true },
        dashboardStats: { activeCourses: 0, enrolledLearners: 0, newsletterSubscribers: 0 },
      },
    });
    await waitFor(() => expect(screen.getByText('Add a course')).toBeInTheDocument());
    expect(screen.queryByText('Overview')).not.toBeInTheDocument();
    expect(screen.queryByText('Active courses')).not.toBeInTheDocument();
  });

  it('shows course and learner stats once there are active courses, including content delivery health', async () => {
    setupFetch('warning');
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: false },
        dashboardStats: { activeCourses: 3, enrolledLearners: 11, newsletterSubscribers: 0 },
      },
    });
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
    expect(screen.getByText('11')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Needs attention')).toBeInTheDocument());
    expect(screen.queryByText('Newsletter subscribers')).not.toBeInTheDocument();
  });

  it('hides the newsletter subscriber stat and quick action when the feature is disabled', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: false },
        dashboardStats: { activeCourses: 2, enrolledLearners: 5, newsletterSubscribers: 9 },
      },
    });
    await waitFor(() => expect(screen.getByText('Add a course')).toBeInTheDocument());
    expect(screen.queryByText('Write a newsletter')).not.toBeInTheDocument();
    expect(screen.queryByText('Newsletter subscribers')).not.toBeInTheDocument();
  });

  it('shows the newsletter subscriber stat and quick action when the org can create a newsletter', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: ['newsletters', 'create_newsletter'],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: true },
        dashboardStats: { activeCourses: 2, enrolledLearners: 5, newsletterSubscribers: 9 },
      },
    });
    await waitFor(() => expect(screen.getByText('Write a newsletter')).toBeInTheDocument());
    expect(screen.getByText('Newsletter subscribers')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
  });

  it('omits a section entirely when dashboardSections leaves it out', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSections: ['overview', 'quick_actions'],
        dashboardSetup: { hasCourse: false, hasTeam: false, profileComplete: false, newsletterConfigured: false },
        dashboardStats: { activeCourses: 3, enrolledLearners: 8, newsletterSubscribers: 0 },
      },
    });
    // Setup checklist would normally show (nothing is done yet), but it's not in dashboardSections.
    await waitFor(() => expect(screen.getByText('Active courses')).toBeInTheDocument());
    expect(screen.queryByText('Finish setting up your organization')).not.toBeInTheDocument();
  });

  it('renders sections in the order given by dashboardSections', async () => {
    const { container } = renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSections: ['quick_actions', 'overview'],
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: false },
        dashboardStats: { activeCourses: 1, enrolledLearners: 2, newsletterSubscribers: 0 },
      },
    });
    await waitFor(() => expect(screen.getByText('Active courses')).toBeInTheDocument());
    const html = container.innerHTML;
    expect(html.indexOf('Quick actions')).toBeLessThan(html.indexOf('Overview'));
  });

  it('renders a named custom component at its configured position', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSections: ['setup_progress', 'custom_component:promo', 'quick_actions'],
        dashboardCustomComponents: {
          promo: { componentTag: '<div data-testid="promo-banner">Upgrade your plan</div>' },
        },
        dashboardSetup: { hasCourse: false, hasTeam: false, profileComplete: false, newsletterConfigured: false },
      },
    });
    await waitFor(() => expect(screen.getByTestId('promo-banner')).toBeInTheDocument());
    expect(screen.getByText('Upgrade your plan')).toBeInTheDocument();
  });

  it('renders multiple named custom components independently', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSections: ['custom_component:top', 'quick_actions', 'custom_component:bottom'],
        dashboardCustomComponents: {
          top: { componentTag: '<div data-testid="top-banner">Top banner</div>' },
          bottom: { componentTag: '<div data-testid="bottom-banner">Bottom banner</div>' },
        },
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: false },
      },
    });
    await waitFor(() => expect(screen.getByTestId('top-banner')).toBeInTheDocument());
    expect(screen.getByTestId('bottom-banner')).toBeInTheDocument();
  });

  it('renders nothing for a custom component slot with no matching configuration', async () => {
    renderWithProviders(<Dashboard />, {
      appContext: {
        localeMessages,
        availableFeatures: [],
        dashboardSections: ['custom_component:unknown', 'quick_actions'],
        dashboardCustomComponents: {},
        dashboardSetup: { hasCourse: true, hasTeam: true, profileComplete: true, newsletterConfigured: false },
      },
    });
    await waitFor(() => expect(screen.getByText('Add a course')).toBeInTheDocument());
  });
});
