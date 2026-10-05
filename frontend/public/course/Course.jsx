import { useEffect, useRef, useState } from 'react'
import render from '../../src/render.jsx';
import Layout from '../components/Layout.jsx';
import EnrollmentForm from '../components/EnrollmentForm.jsx';
import { Alert, Avatar, Box, Button, Card, Container, Dialog, Link, List, ListItem, ListItemIcon, ListItemText, Stack, Typography } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import FormatListBulletedIcon from '@mui/icons-material/FormatListBulleted';
import TranslateIcon from '@mui/icons-material/Translate';
import { alpha, ThemeProvider } from '@mui/material/styles';
import { useAppContext } from '../../src/render.jsx';
import { lightTheme } from '../../src/theme/themes';
import { getReadableTextColor } from '../../src/utils.js';
import { sanitizeEndpointUrl, sanitizeImageUrl, sanitizeUrl } from '../../src/sanitizeUrl.js';
import { sanitizeHtml } from '../../src/sanitizeHtml.js';

// Gap kept between the sticky sidebar and the top of the viewport.
const STICKY_TOP_PX = 24;

const outlinedCardSx = {
    border: '1px solid',
    borderColor: 'border.main',
    boxShadow: 'none',
};

const sectionTitleSx = {
    mb: 2,
    fontSize: '1.25rem',
    fontWeight: 600,
};


function Course() {

    const [displayModal, setDisplayModal] = useState(false);
    const [modalContent, setModalContent] = useState(null);
    const [enrolled, setEnrolled] = useState(false);
    const [showEnrollmentAlert, setShowEnrollmentAlert] = useState(false);
    const [showFixedEnrollBar, setShowFixedEnrollBar] = useState(false);
    const [sidebarFitsViewport, setSidebarFitsViewport] = useState(false);
    const topEnrollButtonRef = useRef(null);
    const sidebarRef = useRef(null);

    const { course, organization, enrollApiUrl: rawEnrollApiUrl, courseLanguageName, localeMessages } = useAppContext();
    const enrollApiUrl = sanitizeEndpointUrl(rawEnrollApiUrl);
    // The course image, the organization logo and the organization's public
    // link are all organization-editable and reach anonymous visitors.
    const courseImage = sanitizeImageUrl(course.image);
    const organizationLogoUrl = sanitizeImageUrl(organization.logo_url);
    const organizationPublicUrl = sanitizeUrl(organization.public_url);
    const hasOrganizationPublicUrl = Boolean(organizationPublicUrl);
    const hasLessons = course.lessons && course.lessons.length > 0;
    const hasInstructors = course.instructors && course.instructors.length > 0;

    const courseDirection = course.is_rtl ? 'rtl' : 'ltr';
    const textAlign = courseDirection === 'rtl' ? 'right' : 'left';

    useEffect(() => {
        const target = topEnrollButtonRef.current;

        if (!target) {
            return undefined;
        }

        const observer = new IntersectionObserver(
            ([entry]) => {
                setShowFixedEnrollBar(!entry.isIntersecting);
            },
            {
                threshold: 0.35,
            }
        );

        observer.observe(target);

        return () => observer.disconnect();
    }, []);

    // The sidebar only sticks when it fits in the viewport; a taller one would
    // pin its bottom out of reach. When it doesn't stick, the enroll button
    // scrolls away like on mobile and the fixed bottom bar takes over.
    useEffect(() => {
        const sidebar = sidebarRef.current;

        if (!sidebar) {
            return undefined;
        }

        const update = () => {
            setSidebarFitsViewport(sidebar.offsetHeight + STICKY_TOP_PX * 2 <= window.innerHeight);
        };

        const observer = new ResizeObserver(update);
        observer.observe(sidebar);
        window.addEventListener('resize', update);
        update();

        return () => {
            observer.disconnect();
            window.removeEventListener('resize', update);
        };
    }, []);

    const showEnrollmentModal = () => {
        setModalContent(
            <EnrollmentForm
                course_title={course.title}
                course_slug={course.slug}
                organization_id={organization.id}
                endpoint={enrollApiUrl}
                autoFocusEmail={true}
                onCancle={() => { setDisplayModal(false); setModalContent(null); }}
                onComplete={() => completeEnrollment()}
                brandColor={organization.brand_color}
            />
        );
        setDisplayModal(true);
    }

    const completeEnrollment = () => {
        setDisplayModal(false);
        setModalContent(null);
        setEnrolled(true);
        setShowEnrollmentAlert(true);
        scrollTo({ top: 0, behavior: 'smooth' });
    }

    const enrollButtonSx = {
        backgroundColor: organization.brand_color,
        color: getReadableTextColor(organization.brand_color),
        '&:hover': { backgroundColor: organization.brand_color, filter: 'brightness(0.9)' },
    };

    const providedBy = (() => {
        const [before, after] = localeMessages['provided_by'].split('ORGANIZATION_NAME');
        return (
            <>
                {before}
                {hasOrganizationPublicUrl ? (
                    <Link href={organizationPublicUrl} target="_blank" rel="noopener noreferrer">
                        {organization.name}
                    </Link>
                ) : (
                    organization.name
                )}
                {after}
            </>
        );
    })();

    const courseFacts = [
        { icon: EmailOutlinedIcon, label: localeMessages['delivered_by_email'] },
        hasLessons && { icon: FormatListBulletedIcon, label: localeMessages['lesson_count'] },
        courseLanguageName && { icon: TranslateIcon, label: `${localeMessages['course_language']}: ${courseLanguageName}` },
    ].filter(Boolean);

    return <ThemeProvider theme={lightTheme}><Layout>
        {enrolled && showEnrollmentAlert && (
            <Alert
                severity="success"
                onClose={() => setShowEnrollmentAlert(false)}
                sx={{ mb: 4, direction: courseDirection }}
            >
                {localeMessages['enrollment_success']}
            </Alert>
        )}

        {/* Two columns on desktop: the course content on one side and a sidebar
            holding the enroll card and the provider/instructors on the other.
            On mobile the sidebar wrapper dissolves (display: contents) so the
            enroll card sits right under the title and the provider/instructors
            drop to the end of the page. */}
        <Box
            sx={{
                direction: courseDirection,
                display: 'grid',
                gap: { xs: 3, md: 4 },
                alignItems: 'start',
                gridTemplateColumns: { xs: 'minmax(0, 1fr)', md: 'minmax(0, 2fr) minmax(0, 1fr)' },
                gridTemplateAreas: {
                    xs: '"header" "enroll" "main" "about"',
                    md: '"header sidebar" "main sidebar"',
                },
                // Keep the header row as short as its content so the main
                // column starts right below the title.
                gridTemplateRows: { md: 'auto 1fr' },
            }}
        >
            {/* Header */}
            <Box sx={{ gridArea: 'header' }}>
                <Typography
                    variant="h1"
                    sx={{
                        fontSize: { xs: '1.6rem', md: '2.25rem' },
                        fontWeight: 700,
                        color: 'text.primary',
                        textAlign: { xs: 'center', md: textAlign },
                        mb: 1,
                    }}
                >
                    {course.title}
                </Typography>
                <Typography
                    variant="body1"
                    sx={{ color: 'text.secondary', fontWeight: 500, textAlign: { xs: 'center', md: textAlign } }}
                >
                    {providedBy}
                </Typography>
            </Box>

            {/* Sidebar */}
            <Box
                ref={sidebarRef}
                sx={{
                    gridArea: 'sidebar',
                    display: { xs: 'contents', md: 'flex' },
                    flexDirection: 'column',
                    gap: 3,
                    position: { md: sidebarFitsViewport ? 'sticky' : 'static' },
                    top: STICKY_TOP_PX,
                }}
            >
                {/* Enroll card */}
                <Card sx={{ ...outlinedCardSx, gridArea: 'enroll', borderRadius: 2 }}>
                    {courseImage ? (
                        <Box
                            component="img"
                            src={courseImage}
                            alt={course.title}
                            sx={{
                                width: '100%',
                                height: 'auto',
                                aspectRatio: '16 / 9',
                                objectFit: 'cover',
                                display: 'block',
                            }}
                        />
                    ) : (
                        <Box
                            sx={{
                                width: '100%',
                                aspectRatio: '16 / 9',
                                backgroundColor: 'grey.600',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}
                        >
                            <AutoStoriesIcon sx={{ fontSize: 64, color: 'common.white' }} />
                        </Box>
                    )}
                    <Box sx={{ p: 2 }}>
                        <Box ref={topEnrollButtonRef}>
                            {!enrolled && (
                                <Button
                                    variant="contained"
                                    size="large"
                                    fullWidth
                                    onClick={showEnrollmentModal}
                                    sx={{ ...enrollButtonSx, fontWeight: 700, mb: 2 }}
                                >
                                    {localeMessages['enroll_now']}
                                </Button>
                            )}
                        </Box>
                        <Stack spacing={1}>
                            {courseFacts.map(({ icon: FactIcon, label }) => (
                                <Stack key={label} direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                                    <FactIcon sx={{ fontSize: '1.25rem', color: 'text.secondary' }} />
                                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                        {label}
                                    </Typography>
                                </Stack>
                            ))}
                        </Stack>
                    </Box>
                </Card>

                {/* Provider and instructors */}
                <Stack spacing={3} sx={{ gridArea: 'about' }}>
                    <Card sx={{ ...outlinedCardSx, p: 2, borderRadius: 2 }}>
                        {organizationLogoUrl && (
                            <Link href={organizationPublicUrl} target="_blank" rel="noopener noreferrer">
                                <Box
                                    component="img"
                                    src={organizationLogoUrl}
                                    alt={`${organization.name} Logo`}
                                    sx={{
                                        display: 'block',
                                        maxWidth: 120,
                                        maxHeight: 80,
                                        height: 'auto',
                                        borderRadius: 1,
                                        mb: 1.5,
                                    }}
                                />
                            </Link>
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.5 }}>
                            {providedBy}
                        </Typography>
                        {organization.description && (
                            <Typography
                                variant="body2"
                                sx={{ color: 'text.secondary', fontSize: '0.875rem' }}
                                dangerouslySetInnerHTML={{ __html: sanitizeHtml(organization.description) }}
                            />
                        )}
                    </Card>

                    {hasInstructors && (
                        <Card sx={{ ...outlinedCardSx, borderRadius: 2 }}>
                            <Typography variant="h2" sx={{ ...sectionTitleSx, fontSize: '1rem', mb: 0, px: 2, pt: 2 }}>
                                {localeMessages['instructors_title']}
                            </Typography>
                            <List disablePadding>
                                {course.instructors.map((instructor, index) => (
                                    <ListItem
                                        key={`${instructor.name}-${index}`}
                                        sx={{ py: 1.25, px: 2, gap: 1.5 }}
                                    >
                                        <Avatar
                                            src={sanitizeImageUrl(instructor.avatar) || undefined}
                                            alt={instructor.name}
                                            sx={{
                                                width: 40,
                                                height: 40,
                                                flexShrink: 0,
                                                bgcolor: organization.brand_color,
                                                color: getReadableTextColor(organization.brand_color),
                                                fontWeight: 600,
                                            }}
                                        >
                                            {instructor.name ? instructor.name[0].toUpperCase() : '?'}
                                        </Avatar>
                                        <ListItemText
                                            primary={instructor.name}
                                            slotProps={{
                                                primary: {
                                                    variant: 'body2',
                                                    sx: { fontWeight: 500, color: 'text.primary', textAlign },
                                                },
                                            }}
                                        />
                                    </ListItem>
                                ))}
                            </List>
                        </Card>
                    )}
                </Stack>
            </Box>

            {/* Main content */}
            <Stack spacing={4} sx={{ gridArea: 'main' }}>
                {course.description && (
                    <Typography
                        variant="body1"
                        sx={{ color: 'text.secondary' }}
                        dangerouslySetInnerHTML={{ __html: sanitizeHtml(course.description) }}
                    />
                )}

                {course.target_audience && (
                    <Box
                        sx={{
                            p: { xs: 2, md: 3 },
                            borderRadius: 2,
                            backgroundColor: (theme) => alpha(theme.palette.background.dark, 0.5),
                        }}
                    >
                        <Typography variant="h2" sx={{ ...sectionTitleSx, mb: 1 }}>
                            {localeMessages['target_audience_title']}
                        </Typography>
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                            {course.target_audience}
                        </Typography>
                    </Box>
                )}

                {hasLessons && (
                    <Box>
                        <Typography variant="h2" sx={sectionTitleSx}>
                            {localeMessages['topics_covered']}
                        </Typography>
                        <Card sx={outlinedCardSx}>
                            <List disablePadding>
                                {course.lessons.map((lesson, index) => (
                                    <ListItem
                                        key={index}
                                        sx={{
                                            py: 1.5,
                                            px: 2,
                                            borderBottom: index < course.lessons.length - 1 ? '1px solid' : 'none',
                                            borderColor: 'border.main',
                                            '&:hover': {
                                                backgroundColor: 'background.box',
                                            },
                                        }}
                                    >
                                        <ListItemIcon
                                            sx={{
                                                minWidth: courseDirection === 'rtl' ? 'auto' : 40,
                                                ml: courseDirection === 'rtl' ? 1 : 0,
                                            }}
                                        >
                                            <CheckCircleIcon
                                                sx={{
                                                    color: organization.brand_color,
                                                    fontSize: '1.5rem',
                                                }}
                                            />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary={lesson}
                                            slotProps={{
                                                primary: {
                                                    variant: 'body2',
                                                    sx: { textAlign },
                                                },
                                            }}
                                        />
                                    </ListItem>
                                ))}
                            </List>
                        </Card>
                    </Box>
                )}

                {course.external_references && course.external_references.length > 0 && (
                    <Box>
                        <Typography variant="h2" sx={sectionTitleSx}>
                            {localeMessages['external_references_title']}
                        </Typography>
                        <Card sx={outlinedCardSx}>
                            <List disablePadding>
                                {course.external_references.map((reference, index) => (
                                    <ListItem
                                        key={`${reference.url}-${index}`}
                                        sx={{
                                            py: 1.5,
                                            px: 2,
                                            borderBottom: index < course.external_references.length - 1 ? '1px solid' : 'none',
                                            borderColor: 'border.main',
                                        }}
                                    >
                                        <ListItemText
                                            primary={
                                                <Link href={sanitizeUrl(reference.url)} target="_blank" rel="noopener noreferrer" underline="hover">
                                                    {reference.name}
                                                </Link>
                                            }
                                            slotProps={{
                                                primary: {
                                                    variant: 'body1',
                                                    sx: { textAlign, wordBreak: 'break-word' },
                                                },
                                            }}
                                        />
                                    </ListItem>
                                ))}
                            </List>
                        </Card>
                    </Box>
                )}
            </Stack>
        </Box>

        {/* Spacer to prevent content from being hidden behind fixed bar */}
        <Box sx={{ pb: 10 }} />

        {/* Enrollment Section - Fixed bottom bar. It appears once the enroll
            button in the sidebar card scrolls out of view, which on desktop only
            happens when the sidebar is too tall to stick. */}
        <Box
            sx={{
                position: 'fixed',
                bottom: 0,
                left: 0,
                right: 0,
                zIndex: 1100,
                px: { xs: 2, md: 4 },
                py: 1.5,
                backgroundColor: (theme) => theme.palette.mode === 'light'
                    ? alpha("#fff", 0.75)
                    : alpha(theme.palette.primary.main, 0.15),
                backdropFilter: 'blur(7px)',
                borderTop: '1px solid',
                borderColor: 'border.main',
                direction: courseDirection,
                opacity: showFixedEnrollBar ? 1 : 0,
                visibility: showFixedEnrollBar ? 'visible' : 'hidden',
                transform: showFixedEnrollBar ? 'translateY(0)' : 'translateY(100%)',
                transition: 'opacity 180ms ease, transform 180ms ease, visibility 180ms ease',
            }}
        >
            <Container maxWidth="lg">
            <Stack
                direction="row"
                spacing={2}
                sx={{ justifyContent: 'space-between', alignItems: 'center' }}
            >
                <Typography variant="body1" sx={{ color: 'text.secondary', fontWeight: 500 }}>
                    {course.title}
                </Typography>
                <Box>
                    {!enrolled &&(
                        <Button
                            variant="contained"
                            size="large"
                            onClick={showEnrollmentModal}
                            sx={enrollButtonSx}
                        >
                            {localeMessages['enroll_now']}
                        </Button>
                    )}
                </Box>
            </Stack>
            </Container>
        </Box>

        <Dialog open={displayModal} onClose={() => setDisplayModal(false)} fullWidth maxWidth="sm">
            {modalContent}
        </Dialog>

    </Layout></ThemeProvider>;
}

render({ children: <Course /> });
