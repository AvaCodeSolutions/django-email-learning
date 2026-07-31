import 'vite/modulepreload-polyfill'
import { useState, useEffect } from 'react'
import { Box, Typography, Grid, LinearProgress, Chip, Link, IconButton } from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import SchoolIcon from '@mui/icons-material/School';
import MailOutlineIcon from '@mui/icons-material/MailOutlined';
import BarChartOutlinedIcon from '@mui/icons-material/BarChartOutlined';
import FavoriteIcon from '@mui/icons-material/Favorite';
import GitHubIcon from '@mui/icons-material/GitHub';
import CloseIcon from '@mui/icons-material/Close';
import Base from '../../src/components/Base.jsx'
import render, { useAppContext } from '../../src/render.jsx';
import apiClient from '../../src/apiClient.js'
import { sanitizeComponentHtml } from '../../src/sanitizeHtml.js';
import { getCookie, setCookie } from '../../src/utils.js'
import { sanitizeEndpointUrl, sanitizeUrl } from '../../src/sanitizeUrl.js';

const DEFAULT_SECTIONS = ['setup_progress', 'overview', 'quick_actions', 'sponsor'];
const CUSTOM_COMPONENT_PREFIX = 'custom_component:';
const GITHUB_SPONSOR_PINK = '#ea4aaa';
const SPONSOR_URL = 'https://github.com/sponsors/AvaCodeSolutions';
const GITHUB_REPO_URL = 'https://github.com/AvaCodeSolutions/django-email-learning';
const DASHBOARD_SECTIONS_DOCS_URL = 'https://django-email-learning.readthedocs.io/en/latest/installation.html#dashboard-sections';
const SPONSOR_DISMISSED_COOKIE = 'dashboard_sponsor_dismissed';

function SectionBox({ children, sx = {} }) {
  return (
    <Box sx={{
      p: { xs: 1.5, sm: 2.5 },
      borderRadius: { xs: 0, sm: 2 },
      backgroundColor: 'background.box',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)',
      ...sx,
    }}>
      {children}
    </Box>
  )
}

function SetupItem({ item }) {
  return (
    <Box sx={{
      display: 'flex', alignItems: 'flex-start', gap: 1.5, py: 1.75,
      borderTop: '1px solid', borderColor: 'divider',
    }}>
      {item.done
        ? <CheckCircleIcon sx={{ color: 'secondary.main', mt: '2px' }} fontSize="small" />
        : <RadioButtonUncheckedIcon sx={{ color: 'text.disabled', mt: '2px' }} fontSize="small" />}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, ...(item.done && { color: 'text.secondary', textDecoration: 'line-through' }) }}>
          {item.title}
        </Typography>
        <Typography variant="body2" color="text.secondary">{item.description}</Typography>
      </Box>
      {!item.done && (
        <Link href={item.href} underline="none" sx={(theme) => ({
          flexShrink: 0, fontSize: '0.85rem', fontWeight: 500,
          border: `1px solid ${theme.palette.border.main}`, borderRadius: 2,
          px: 1.75, py: 0.75, whiteSpace: 'nowrap',
        })}>
          {item.cta}
        </Link>
      )}
    </Box>
  )
}

function StatCard({ label, value }) {
  return (
    <SectionBox sx={{ height: '100%' }}>
      <Typography sx={{ fontSize: '1.7rem', fontWeight: 700, letterSpacing: '-0.01em', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>{label}</Typography>
    </SectionBox>
  )
}

function HealthStatCard({ label, statusLabel, health }) {
  const color = health === 'healthy' ? 'success' : health === 'warning' ? 'warning' : 'error';
  return (
    <SectionBox sx={{ height: '100%' }}>
      <Chip size="small" color={color} label={statusLabel} sx={{ fontWeight: 600 }} />
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{label}</Typography>
    </SectionBox>
  )
}

function ActionCard({ icon, title, description, cta, href }) {
  return (
    <SectionBox sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Box sx={{
        width: 34, height: 34, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center',
        backgroundColor: 'background.dark', color: 'primary.main',
      }}>
        {icon}
      </Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>{title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>{description}</Typography>
      <Link href={href} underline="hover" sx={{ fontSize: '0.85rem', fontWeight: 500 }}>{cta} →</Link>
    </SectionBox>
  )
}

function SetupProgressSection({ localeMessages, setupItems, doneCount, totalCount, setupComplete }) {
  if (setupComplete) return null;
  return (
    <Grid size={{ xs: 12 }}>
      <SectionBox>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1.5, flexWrap: 'wrap' }}>
          <Typography variant="h6">{localeMessages.setup_checklist_title}</Typography>
          <Chip
            size="small"
            label={localeMessages.setup_progress.replace('DONE', doneCount).replace('TOTAL', totalCount)}
          />
        </Box>
        <LinearProgress
          variant="determinate"
          value={(doneCount / totalCount) * 100}
          sx={{ mt: 1.5, mb: 0.5, height: 6, borderRadius: 3 }}
        />
        {setupItems.map((item) => <SetupItem key={item.key} item={item} />)}
      </SectionBox>
    </Grid>
  )
}

function OverviewSection({ localeMessages, statCards }) {
  if (statCards.length === 0) return null;
  return (
    <>
      <Grid size={{ xs: 12 }}>
        <Typography variant="overline" color="text.disabled">{localeMessages.overview_title}</Typography>
      </Grid>
      {statCards.map((stat) => (
        <Grid key={stat.key} size={{ xs: 6, sm: 6, md: 3 }}>
          {stat.isHealth
            ? <HealthStatCard label={stat.label} statusLabel={stat.statusLabel} health={stat.health} />
            : <StatCard label={stat.label} value={stat.value} />}
        </Grid>
      ))}
    </>
  )
}

function QuickActionsSection({ localeMessages, platformBaseUrl, canCreateNewsletter, orgScopedUrl }) {
  return (
    <>
      <Grid size={{ xs: 12 }}>
        <Typography variant="overline" color="text.disabled">{localeMessages.quick_actions_title}</Typography>
      </Grid>
      <Grid size={{ xs: 12, sm: 6, md: canCreateNewsletter ? 4 : 6 }}>
        <ActionCard
          icon={<SchoolIcon fontSize="small" />}
          title={localeMessages.action_add_course_title}
          description={localeMessages.action_add_course_description}
          cta={localeMessages.action_add_course_cta}
          href={`${platformBaseUrl}/courses/`}
        />
      </Grid>
      {canCreateNewsletter && (
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <ActionCard
            icon={<MailOutlineIcon fontSize="small" />}
            title={localeMessages.action_write_newsletter_title}
            description={localeMessages.action_write_newsletter_description}
            cta={localeMessages.action_write_newsletter_cta}
            href={orgScopedUrl('newsletters')}
          />
        </Grid>
      )}
      <Grid size={{ xs: 12, sm: 6, md: canCreateNewsletter ? 4 : 6 }}>
        <ActionCard
          icon={<BarChartOutlinedIcon fontSize="small" />}
          title={localeMessages.action_view_analytics_title}
          description={localeMessages.action_view_analytics_description}
          cta={localeMessages.action_view_analytics_cta}
          href={`${platformBaseUrl}/analytics/`}
        />
      </Grid>
    </>
  )
}

function CustomComponentSection({ component }) {
  if (!component?.componentTag) return null;
  return (
    <Grid size={{ xs: 12 }}>
      <Box dangerouslySetInnerHTML={{ __html: sanitizeComponentHtml(component.componentTag) }} />
    </Grid>
  )
}

function SponsorSection({ localeMessages }) {
  const [dismissed, setDismissed] = useState(() => getCookie(SPONSOR_DISMISSED_COOKIE) === '1');

  if (dismissed) return null;

  const handleDismiss = () => {
    setCookie(SPONSOR_DISMISSED_COOKIE, '1');
    setDismissed(true);
  };

  return (
    <>
      <Grid size={{ xs: 12 }}>
        <Typography variant="overline" color="text.disabled">{localeMessages.sponsor_section_title}</Typography>
      </Grid>
      <Grid size={{ xs: 12 }}>
      <SectionBox sx={{ textAlign: 'center', position: 'relative' }}>
        <IconButton
          onClick={handleDismiss}
          aria-label={localeMessages.sponsor_dismiss_label}
          size="small"
          sx={{ position: 'absolute', top: 8, right: 8, color: 'text.disabled' }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
        <FavoriteIcon sx={{ color: GITHUB_SPONSOR_PINK, fontSize: 28, mb: 1 }} />
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>{localeMessages.sponsor_title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 480, mx: 'auto' }}>
          {localeMessages.sponsor_description}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1.5, justifyContent: 'center', flexWrap: 'wrap', mt: 2 }}>
          <Link
            href={SPONSOR_URL}
            target="_blank"
            rel="noopener noreferrer"
            underline="none"
            sx={(theme) => ({
              display: 'inline-flex', alignItems: 'center', gap: 0.75,
              fontSize: '0.85rem', fontWeight: 500,
              border: `1px solid ${theme.palette.border.main}`, borderRadius: 2, px: 2, py: 1,
            })}
          >
            <FavoriteIcon sx={{ fontSize: '1rem', color: GITHUB_SPONSOR_PINK }} />
            {localeMessages.sponsor_cta}
          </Link>
          <Link
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            underline="none"
            sx={(theme) => ({
              display: 'inline-flex', alignItems: 'center', gap: 0.75,
              fontSize: '0.85rem', fontWeight: 500,
              border: `1px solid ${theme.palette.border.main}`, borderRadius: 2, px: 2, py: 1,
            })}
          >
            <GitHubIcon sx={{ fontSize: '1rem', color: '#000' }} />
            {localeMessages.sponsor_star_cta}
          </Link>
        </Box>
        <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 2 }}>
          {localeMessages.sponsor_remove_note}{' '}
          <Link href={DASHBOARD_SECTIONS_DOCS_URL} target="_blank" rel="noopener noreferrer">
            {localeMessages.sponsor_docs_link_label}
          </Link>
        </Typography>
      </SectionBox>
      </Grid>
    </>
  )
}

function Dashboard() {
  const {
    localeMessages, apiBaseUrl: rawApiBaseUrl, platformBaseUrl: rawPlatformBaseUrl, greetingName, activeOrganizationName,
    dashboardSetup = {}, dashboardStats = {}, availableFeatures = [],
    dashboardSections, dashboardCustomComponents = {}, isPlatformAdmin,
  } = useAppContext();
  const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
  const platformBaseUrl = sanitizeUrl(rawPlatformBaseUrl);
  const [organizationId, setOrganizationId] = useState(null);
  const [jobHealth, setJobHealth] = useState(null);

  const newslettersEnabled = availableFeatures.includes('newsletters');
  const canCreateNewsletter = newslettersEnabled && availableFeatures.includes('create_newsletter');

  useEffect(() => {
    // Job status is platform-admin only, so the delivery health card below is
    // too - skip the request entirely for everyone else.
    if (!isPlatformAdmin) {
      return;
    }
    apiClient.get(`${apiBaseUrl}/status/jobs/`)
      .then(data => setJobHealth(data.jobs?.deliver_contents?.job_health_status || null))
      .catch(() => {});
  }, [apiBaseUrl, isPlatformAdmin]);

  const orgScopedUrl = (tab) => organizationId
    ? `${platformBaseUrl}/organizations/${organizationId}/?tab=${tab}`
    : `${platformBaseUrl}/organizations/`;

  const setupItems = [
    {
      key: 'course',
      done: Boolean(dashboardSetup.hasCourse),
      title: localeMessages.setup_course_title,
      description: localeMessages.setup_course_description,
      cta: localeMessages.setup_course_cta,
      href: `${platformBaseUrl}/courses/`,
    },
    {
      key: 'team',
      done: Boolean(dashboardSetup.hasTeam),
      title: localeMessages.setup_team_title,
      description: localeMessages.setup_team_description,
      cta: localeMessages.setup_team_cta,
      href: orgScopedUrl('members'),
    },
    {
      key: 'profile',
      done: Boolean(dashboardSetup.profileComplete),
      title: localeMessages.setup_profile_title,
      description: localeMessages.setup_profile_description,
      cta: localeMessages.setup_profile_cta,
      href: orgScopedUrl('general_info'),
    },
    ...(canCreateNewsletter ? [{
      key: 'newsletter',
      done: Boolean(dashboardSetup.newsletterConfigured),
      title: localeMessages.setup_newsletter_title,
      description: localeMessages.setup_newsletter_description,
      cta: localeMessages.setup_newsletter_cta,
      href: orgScopedUrl('newsletters'),
    }] : []),
  ];
  const doneCount = setupItems.filter((item) => item.done).length;
  const totalCount = setupItems.length;
  const setupComplete = doneCount === totalCount;

  const hasActiveCourses = Number(dashboardStats.activeCourses) > 0;
  const hasNewsletterSubscribers = newslettersEnabled && Number(dashboardStats.newsletterSubscribers) > 0;

  const statCards = [
    hasActiveCourses && { key: 'courses', label: localeMessages.stat_active_courses, value: dashboardStats.activeCourses },
    hasActiveCourses && { key: 'learners', label: localeMessages.stat_enrolled_learners, value: dashboardStats.enrolledLearners },
    hasNewsletterSubscribers && { key: 'subscribers', label: localeMessages.stat_newsletter_subscribers, value: dashboardStats.newsletterSubscribers },
    hasActiveCourses && jobHealth && {
      key: 'health',
      label: localeMessages.stat_content_delivery_health,
      statusLabel: localeMessages[`content_delivery_${jobHealth}`] || jobHealth,
      health: jobHealth,
      isHealth: true,
    },
  ].filter(Boolean);

  const greetingText = greetingName
    ? localeMessages.welcome_back_name.replace('NAME', greetingName)
    : localeMessages.welcome_back;

  const sections = dashboardSections?.length ? dashboardSections : DEFAULT_SECTIONS;

  const renderSection = (sectionKey) => {
    if (sectionKey.startsWith(CUSTOM_COMPONENT_PREFIX)) {
      const name = sectionKey.slice(CUSTOM_COMPONENT_PREFIX.length);
      return <CustomComponentSection key={sectionKey} component={dashboardCustomComponents[name]} />;
    }
    switch (sectionKey) {
      case 'setup_progress':
        return (
          <SetupProgressSection
            key={sectionKey}
            localeMessages={localeMessages}
            setupItems={setupItems}
            doneCount={doneCount}
            totalCount={totalCount}
            setupComplete={setupComplete}
          />
        );
      case 'overview':
        return <OverviewSection key={sectionKey} localeMessages={localeMessages} statCards={statCards} />;
      case 'quick_actions':
        return (
          <QuickActionsSection
            key={sectionKey}
            localeMessages={localeMessages}
            platformBaseUrl={platformBaseUrl}
            canCreateNewsletter={canCreateNewsletter}
            orgScopedUrl={orgScopedUrl}
          />
        );
      case 'sponsor':
        return <SponsorSection key={sectionKey} localeMessages={localeMessages} />;
      default:
        return null;
    }
  };

  return (
    <Base breadCrumbList={[]} organizationIdRefreshCallback={setOrganizationId}>
      <Grid size={{ xs: 12 }} sx={{ py: 2, pl: { xs: 1.5, sm: 2 }, pr: { xs: 1.5 } }}>
        <Grid container spacing={3}>

          <Grid size={{ xs: 12 }}>
            <Typography variant="h4" sx={{ fontWeight: 600 }}>{greetingText}</Typography>
            {activeOrganizationName && (
              <Typography variant="body1" color="text.secondary">
                {localeMessages.dashboard_subtitle.replace('ORGANIZATION_NAME', activeOrganizationName)}
              </Typography>
            )}
          </Grid>

          {sections.map(renderSection)}

        </Grid>
      </Grid>
    </Base>
  )
}

export default Dashboard;

render({children: <Dashboard />});
