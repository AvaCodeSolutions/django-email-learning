import { useEffect, useRef, useState } from 'react'
import render from '../../src/render.jsx';
import Layout from '../components/Layout.jsx';
import EnrollmentForm from '../components/EnrollmentForm.jsx';
import { Alert, Box, Button, Card, Chip, Container, Dialog, Grid, Link, List, ListItem, ListItemIcon, ListItemText, Stack, Typography } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import { alpha, ThemeProvider } from '@mui/material/styles';
import { useAppContext } from '../../src/render.jsx';
import { lightTheme } from '../../src/theme/themes';
import { getReadableTextColor } from '../../src/utils.js';
import { sanitizeEndpointUrl, sanitizeImageUrl, sanitizeUrl } from '../../src/sanitizeUrl.js';


function Course() {

    const [displayModal, setDisplayModal] = useState(false);
    const [modalContent, setModalContent] = useState(null);
    const [enrolled, setEnrolled] = useState(false);
    const [showEnrollmentAlert, setShowEnrollmentAlert] = useState(false);
    const [showFixedEnrollBar, setShowFixedEnrollBar] = useState(false);
    const topEnrollButtonRef = useRef(null);

    const { course, organization, enrollApiUrl: rawEnrollApiUrl, localeMessages } = useAppContext();
    const enrollApiUrl = sanitizeEndpointUrl(rawEnrollApiUrl);
    // The course image, the organization logo and the organization's public
    // link are all organization-editable and reach anonymous visitors.
    const courseImage = sanitizeImageUrl(course.image);
    const organizationLogoUrl = sanitizeImageUrl(organization.logo_url);
    const organizationPublicUrl = sanitizeUrl(organization.public_url);

    const courseDirection = course.is_rtl ? 'rtl' : 'ltr';

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

    return <ThemeProvider theme={lightTheme}><Layout>
        {/* Course Header with Image and Title */}
        <Typography
                variant="h1"
                sx={{
                    display: { xs: 'block', md: 'none' },
                    textAlign: 'center',
                    mb: 2,
                    fontSize: '1.6rem',
                    color: 'text.primary',
                }}
            >
                {course.title}
            </Typography>
        <Box
            sx={{
                mb: 4,
                borderRadius: 2,
                overflow: 'hidden',
                backgroundColor: { xs: 'background.paper', md: 'background.dark' },
                direction: courseDirection,
                position: 'relative',
            }}
        >


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
                        aspectRatio: { xs: '16 / 9', md: '32 / 9' },
                        backgroundColor: 'grey.600',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}
                >
                    <AutoStoriesIcon sx={{ fontSize: 64, color: 'common.white' }} />
                </Box>
            )}

            <Box
                sx={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'flex-end',
                    p: { xs: 2, md: 3 },
                    background: course.image
                        ? 'linear-gradient(180deg, rgba(0, 0, 0, 0) 25%, rgba(0, 0, 0, 0.75) 100%)'
                        : 'none',
                    pointerEvents: 'none',
                }}
            >
                <Stack
                    direction={courseDirection === 'rtl' ? 'row-reverse' : 'row'}
                    spacing={2}
                    sx={{
                        justifyContent: { xs: 'center', md: 'space-between' },
                        alignItems: { xs: 'center', md: 'flex-end' },
                        width: '100%',
                    }}
                >
                    <Typography
                        variant="h1"
                        sx={{
                            display: { xs: 'none', md: 'block' },
                            color: 'common.white',
                            maxWidth: { xs: '100%', md: '70%' },
                            fontSize: '2rem',
                            textShadow: '0 6px 24px rgba(0, 0, 0, 0.45)',
                        }}
                    >
                        {course.title}
                    </Typography>
                    <Box
                        ref={topEnrollButtonRef}
                    sx={{
                        pointerEvents: 'auto',
                        flexShrink: 0,
                        mx: { xs: 'auto', md: 0 },
                    }}
                    >
                        {!enrolled && (
                            <Button
                                variant="contained"
                                size="large"
                                onClick={showEnrollmentModal}
                                sx={{
                                    minWidth: { xs: 160, sm: 190 },
                                    boxShadow: '0 16px 40px rgba(0, 0, 0, 0.28)',
                                    border: 'solid 1px #ffffff30',
                                    fontWeight: 700,
                                    backgroundColor: organization.brand_color,
                                    color: getReadableTextColor(organization.brand_color),
                                    '&:hover': { backgroundColor: organization.brand_color, filter: 'brightness(0.9)' },
                                }}
                            >
                                {localeMessages['enroll_now']}
                            </Button>
                        )}
                    </Box>
                </Stack>
            </Box>
        </Box>
        {enrolled && showEnrollmentAlert && (
            <Alert
                severity="success"
                onClose={() => setShowEnrollmentAlert(false)}
                sx={{ mb: 4, direction: courseDirection }}
            >
                {localeMessages['enrollment_success']}
            </Alert>
        )}

        {/* Course Info Section */}
        <Box
            sx={{
                p: { xs: 2, md: 3 },
                mb: 4,
                borderRadius: 2,
                backgroundColor: (theme) => theme.palette.mode === 'light'
                    ? alpha(theme.palette.background.dark, 0.5)
                    : alpha(theme.palette.common.white, 0.04),
                direction: courseDirection,
            }}
        >
            <Stack spacing={{ xs: 2, md: 5 }}>

                {course.description && (
                    <Typography
                        variant="body1"
                        sx={{ color: 'text.secondary' }}
                    >
                        {course.description}
                    </Typography>
                )}

                {/* Organization Info */}
                <Box
                    sx={{
                        p: 2,
                        borderRadius: 2,
                        backgroundColor: "white",
                    }}
                >
                    <Grid container spacing={2}>
                    {organizationLogoUrl && (
                        <Grid size={{ xs: 12, md: 3 }} sx={{ mx: 'auto', textAlign: 'center' }}>
                            <Link href={organizationPublicUrl} target="_blank" rel="noopener noreferrer">
                                <Box
                                    component="img"
                                    src={organizationLogoUrl}
                                    alt={`${organization.name} Logo`}
                                    sx={{
                                        maxWidth: 120,
                                    height: 'auto',
                                    borderRadius: 1,
                                }}
                            /></Link>
                        </Grid>
                    )}
                        <Grid size={{ xs: 12, md: organizationLogoUrl ? 9 : 12 }} sx={{ mx: 'auto', mt: 2 }}>

                            <Typography variant="body2" sx={{ fontWeight: 500, color: 'text.secondary' }}>
                                {(() => {
                                    const [before, after] = localeMessages['provided_by'].split('ORGANIZATION_NAME');
                                    return (
                                        <>
                                            {before}
                                            <a href={sanitizeEndpointUrl(organizationPublicUrl)} rel="noopener noreferrer">{organization.name}</a>
                                            {after}
                                        </>
                                    );
                                })()}
                            </Typography>
                            {organization.description && (
                                <Typography
                                    variant="body2"
                                    sx={{ color: 'text.secondary', fontSize: '0.875rem' }}
                                >
                                    {organization.description}
                                </Typography>
                            )}
                        </Grid>
                    </Grid>
                </Box>

                {course.target_audience && (
                    <Box sx={{ py: 1 }}>
                        <Typography variant="h2" sx={{ mb: 1, direction: courseDirection, fontSize: '1.25rem', fontWeight: 600 }}>
                            {localeMessages['target_audience_title']}
                        </Typography>
                        <Typography
                            variant="body2"
                            sx={{ color: 'text.secondary', direction: courseDirection }}
                        >
                            {course.target_audience}
                        </Typography>
                    </Box>
                )}

            </Stack>
        </Box>

        {/* Topics/Lessons Section */}
        {course.lessons && course.lessons.length > 0 && (
            <Box sx={{ my: 4 }}>
                <Typography variant="h2" sx={{ mb: 2, direction: courseDirection, fontSize: '1.25rem' }}>
                    {localeMessages['topics_covered']}
                </Typography>
                <Card
                    sx={{
                        border: '1px solid',
                        borderColor: 'border.main',
                        boxShadow: 'none',
                    }}
                >
                    <List sx={{ direction: courseDirection }}>
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
                                            sx: {
                                                textAlign: courseDirection === 'rtl' ? 'right' : 'left',
                                            },
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
            <Box sx={{ my: 4 }}>
                <Typography variant="h2" sx={{ direction: courseDirection, fontSize: '1.25rem' }}>
                    {localeMessages['external_references_title']}
                </Typography>
                <Card
                    sx={{
                        border: '1px solid',
                        borderColor: 'border.main',
                        boxShadow: 'none',
                    }}
                >
                    <List sx={{ direction: courseDirection }}>
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
                                            sx: {
                                                textAlign: courseDirection === 'rtl' ? 'right' : 'left',
                                                wordBreak: 'break-word',
                                            },
                                        },
                                    }}
                                />
                            </ListItem>
                        ))}
                    </List>
                </Card>
            </Box>
        )}

        {/* Spacer to prevent content from being hidden behind fixed bar */}
        <Box sx={{ pb: 10 }} />

        {/* Enrollment Section - Fixed bottom bar */}
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
                            sx={{
                                backgroundColor: organization.brand_color,
                                color: getReadableTextColor(organization.brand_color),
                                '&:hover': { backgroundColor: organization.brand_color, filter: 'brightness(0.9)' },
                            }}
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
