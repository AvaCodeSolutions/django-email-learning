import { useState, useEffect } from 'react'
import render from '../../src/render.jsx';
import Layout from '../components/Layout.jsx';
import EnrollmentForm from '../components/EnrollmentForm.jsx';
import NewsletterSubscriptionForm from '../components/NewsletterSubscriptionForm.jsx';
import { Alert, Box, Button, Card, CardContent, CardMedia, Dialog, Grid, IconButton, Stack, SvgIcon, Tooltip, Typography, Link } from '@mui/material';
import LanguageIcon from '@mui/icons-material/Language';
import LinkedInIcon from '@mui/icons-material/LinkedIn';
import YouTubeIcon from '@mui/icons-material/YouTube';
import FacebookIcon from '@mui/icons-material/Facebook';
import InstagramIcon from '@mui/icons-material/Instagram';
import TelegramIcon from '@mui/icons-material/Telegram';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import XIcon from '@mui/icons-material/X';
import LinkIcon from '@mui/icons-material/Link';
import SchoolIcon from '@mui/icons-material/School';
import { alpha, ThemeProvider } from '@mui/material/styles';
import { useAppContext } from '../../src/render.jsx';
import { lightTheme } from '../../src/theme/themes';
import { getReadableTextColor } from '../../src/utils.js';
import { sanitizeEndpointUrl, sanitizeImageUrl, sanitizeUrl } from '../../src/sanitizeUrl.js';


// No Material UI icon exists for these brands, so their marks are reproduced
// here as plain SvgIcon path data. Unlike most MUI social icons (which draw a
// padded badge shape around the mark), these paths fill their box edge to
// edge, so the viewBox is padded out here to match the others' visual weight.
function TikTokIcon(props) {
    return (
        <SvgIcon {...props} viewBox="-3 -3 30 30">
            <path d="M12.53.02c1.31-.02 2.61-.01 3.9-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.43 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
        </SvgIcon>
    );
}

function SubstackIcon(props) {
    return (
        <SvgIcon {...props} viewBox="-3 -3 30 30">
            <path d="M22.539 8.242H1.46V5.406h21.08v2.836zM1.46 10.812V24L12 18.11 22.54 24V10.812H1.46zM22.539 0H1.46v2.836h21.08V0z" />
        </SvgIcon>
    );
}

const SOCIAL_LINK_ICONS = {
    website: LanguageIcon,
    youtube: YouTubeIcon,
    linkedin: LinkedInIcon,
    facebook: FacebookIcon,
    instagram: InstagramIcon,
    tiktok: TikTokIcon,
    x: XIcon,
    whatsapp: WhatsAppIcon,
    telegram: TelegramIcon,
    substack: SubstackIcon,
};

// MUI's own X icon (unlike Facebook/Instagram/etc.) draws the bare logotype
// with no padded badge shape around it, so it reads visually larger/bolder
// than the others at the same fontSize unless scaled down slightly here.
const COMPACT_ICON_PLATFORMS = new Set(['x']);

// Per-brand hover styling. `website` is intentionally omitted - it isn't a
// real brand, so it keeps the generic indigo hover used as the fallback.
const BRAND_HOVER_STYLES = {
    youtube: { backgroundColor: '#ff0000', color: '#ffffff', borderColor: '#ff0000' },
    x: { backgroundColor: '#000000', color: '#ffffff', borderColor: '#000000' },
    substack: { backgroundColor: '#ff6719', color: '#ffffff', borderColor: '#ff6719' },
    facebook: { backgroundColor: '#1877f2', color: '#ffffff', borderColor: '#1877f2' },
    // Instagram's real mark is a gradient; this is a commonly used single-color stand-in.
    instagram: { backgroundColor: '#e4405f', color: '#ffffff', borderColor: '#e4405f' },
    linkedin: { backgroundColor: '#0a66c2', color: '#ffffff', borderColor: '#0a66c2' },
    whatsapp: { backgroundColor: '#25d366', color: '#ffffff', borderColor: '#25d366' },
    telegram: { backgroundColor: '#26a5e4', color: '#ffffff', borderColor: '#26a5e4' },
    tiktok: { backgroundColor: '#000000', color: '#ffffff', borderColor: '#000000' },
};

const SOCIAL_LINK_LABEL_KEYS = {
    website: 'website',
    youtube: 'youtube_channel',
    linkedin: 'linkedin_page',
    facebook: 'facebook_page',
    instagram: 'instagram',
    tiktok: 'tiktok',
    x: 'twitter_x',
    whatsapp: 'whatsapp_channel',
    telegram: 'telegram_channel',
    substack: 'substack',
};

function Organization() {

    const [displayModal, setDisplayModal] = useState(false);
    const [modalContent, setModalContent] = useState(null);
    const [courses, setCourses] = useState([]);
    const [showSuccessMessage, setShowSuccessMessage] = useState(false);

    const { organization, enrollApiUrl: rawEnrollApiUrl, newsletterSubscribeApiUrl: rawNewsletterSubscribeApiUrl, newsletters = [], localeMessages } = useAppContext();
    const enrollApiUrl = sanitizeEndpointUrl(rawEnrollApiUrl);
    const newsletterSubscribeApiUrl = sanitizeEndpointUrl(rawNewsletterSubscribeApiUrl);
    // The logo, the course images and the social links are all
    // organization-editable and reach anonymous visitors.
    const organizationLogoUrl = sanitizeImageUrl(organization["logo_url"]);

    const hasMultipleLanguages = new Set(courses.map((course) => course.language)).size > 1;

    useEffect(() => {
        const initialCourses = (organization.courses || []).map((course) => ({ ...course, enrolled: false }));
        setCourses(initialCourses);
    }, []);

    const showModalForCourse = (course) => {
        // Logic to show modal for specific course
        setModalContent(<EnrollmentForm course_title={course.title} course_slug={course.slug} organization_id={organization.id} endpoint={enrollApiUrl} autoFocusEmail={true} onCancle={() => {setDisplayModal(false); setModalContent(null);}} onComplete={() => completeEnrollment(course)} newsletter_id={course.newsletter_id || null} newsletter_title={course.newsletter_title || null} brandColor={organization.brand_color} />);
        setDisplayModal(true);
    }

    const completeEnrollment = (course) => {
        setDisplayModal(false);
        setModalContent(null);
        // Disable the enrolled course button
        let updatedCourses = courses.map(c => {
            if (c.id === course.id) {
                return { ...c, enrolled: true };
            }
            return c;
        });
        setCourses(updatedCourses);
        setShowSuccessMessage(true);
    }


    return <ThemeProvider theme={lightTheme}><Layout>
        <Box
            sx={{
                p: { xs: 2, md: 3 },
                mb: 4,
                borderRadius: 2,
                backgroundColor: (theme) => theme.palette.mode === 'light'
                    ? '#fafafa'
                    : alpha(theme.palette.common.white, 0.04),
            }}
        >
            <Stack
                direction={{ xs: 'column', md: 'row' }}
                spacing={{ xs: 2, md: 3 }}
                sx={{ alignItems: { xs: 'stretch', md: 'flex-start' } }}
            >
                { organizationLogoUrl &&
                    <Box sx={{ flexShrink: 0, textAlign: { xs: 'center', md: 'left' } }}>
                        <Box component="img" src={ organizationLogoUrl } alt={`${organization["name"]} Logo`} sx={{ maxWidth: 220, width: '100%', height: 'auto' }} />
                    </Box>
                }
                <Stack spacing={2} sx={{ flex: 1, minWidth: 0, pt: { xs: 1, md: 3 }, px: { xs: 0.5, md: 1 } }}>
                    <Typography variant="h1" sx={{ mb: 0, fontSize: '1.75rem', textAlign: { xs: 'center', md: 'left' } }}>{ organization["name"] }</Typography>
                    <Typography variant="body1" sx={{ color: 'text.secondary' }}>{ organization["description"] }</Typography>
                    {organization.social_links && organization.social_links.length > 0 && (
                        <Stack
                            direction="row"
                            spacing={1}
                            useFlexGap
                            sx={{ pt: 1, alignItems: 'center', justifyContent: { xs: 'center', md: 'flex-start' }, flexWrap: 'wrap' }}
                        >
                            {organization.social_links.map((link) => {
                                const Icon = SOCIAL_LINK_ICONS[link.platform] || LinkIcon;
                                const labelKey = SOCIAL_LINK_LABEL_KEYS[link.platform];
                                const label = localeMessages[labelKey] || link.platform;
                                const brandHover = BRAND_HOVER_STYLES[link.platform];
                                return (
                                    <Tooltip key={link.platform} title={label}>
                                        <IconButton
                                            component="a"
                                            href={sanitizeUrl(link.url)}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            aria-label={label}
                                            sx={{
                                                color: 'text.secondary',
                                                border: '1px solid',
                                                borderColor: (theme) => alpha(theme.palette.text.secondary, 0.3),
                                                transition: 'background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease',
                                                '&:hover': brandHover || {
                                                    color: 'primary.main',
                                                    borderColor: (theme) => alpha(theme.palette.primary.main, 0.5),
                                                },
                                            }}
                                        >
                                            <Icon fontSize="small" sx={COMPACT_ICON_PLATFORMS.has(link.platform) ? { fontSize: '1.05rem' } : undefined} />
                                        </IconButton>
                                    </Tooltip>
                                );
                            })}
                        </Stack>
                    )}
                </Stack>
            </Stack>
        </Box>
        {showSuccessMessage && (
            <Alert
                severity="success"
                onClose={() => setShowSuccessMessage(false)}
                sx={{ mb: 4 }}
            >
                {localeMessages['enrollment_success']}
            </Alert>
        )}

        <Box sx={{ my: 4 }}>
            <Typography variant="h2" sx={{ mb: 2, fontSize: '1.375rem', pl: { xs: 0.5, md: 1 } }}>{localeMessages['courses']}</Typography>
            { courses.length > 0 ? (
                <Grid container columnSpacing={2} rowSpacing={3} sx={{ alignItems: 'stretch' }}>
                { courses.map((course) => {
                    const courseDirection = course.is_rtl ? 'rtl' : 'ltr';
                    return (
                    <Grid size={{ xs: 12, sm: 6, md: 4 }} key={course["id"]} sx={{ display: 'flex' }}>
                        <Card
                            key={course["id"]}
                            sx={{
                                height: '100%',
                                width: '100%',
                                display: 'flex',
                                flexDirection: 'column',
                                border: '1px solid',
                                borderColor: 'border.main',
                                boxShadow: 'none',
                                transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
                                '&:hover': {
                                    boxShadow: (theme) => theme.palette.mode === 'dark'
                                        ? '0 8px 18px rgba(0,0,0,0.28)'
                                        : '0 8px 18px rgba(16,24,40,0.10)',
                                },
                            }}
                        >
                            <CardMedia
                                component={course["image"] ? "img" : "div"}
                                image={sanitizeImageUrl(course["image"])}
                                sx={{
                                    aspectRatio: '16 / 9',
                                    backgroundColor: 'background.dark',
                                    objectFit: 'cover',
                                    display: course["image"] ? undefined : 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    borderBottom: '1px solid',
                                    borderColor: organization.brand_color ? alpha(organization.brand_color, 0.2) : 'border.main',
                                }}
                            >
                                {course["image"] ? null : (
                                    <SchoolIcon sx={{ fontSize: 48, color: 'grey.400' }} />
                                )}
                            </CardMedia>
                            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.25, flexGrow: 1, direction: course.is_rtl ? 'rtl' : 'ltr' }}>
                                <Box>
                                    <Link href={`courses/${course["slug"]}/`} underline="none">
                                        <Typography variant="h3" sx={{ fontSize: '1.125rem', textAlign: courseDirection === 'rtl' ? 'right' : 'left' }}>{course["title"]}</Typography>
                                    </Link>
                                    {hasMultipleLanguages && (
                                        <Stack direction={courseDirection === 'rtl' ? 'rtl' : 'ltr'} spacing={0.5} sx={{ mt: 0.25, alignItems: 'center' }}>
                                            <LanguageIcon
                                                sx={(theme) => ({
                                                    fontSize: '1rem',
                                                    color: theme.palette.grey[600],
                                                })}
                                            />
                                            <Typography
                                                variant="body2"
                                                sx={(theme) => ({
                                                    fontSize: '0.875rem',
                                                    color: theme.palette.grey[600],
                                                    textAlign: courseDirection === 'rtl' ? 'right' : 'left',
                                                })}
                                            >
                                                {course["language"]}
                                            </Typography>
                                        </Stack>
                                    )}
                                </Box>
                                <Typography
                                    variant="body2"
                                    sx={{
                                        color: 'text.secondary',
                                        textAlign: courseDirection === 'rtl' ? 'right' : 'left',
                                        display: '-webkit-box',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        WebkitLineClamp: 4,
                                        WebkitBoxOrient: 'vertical',
                                    }}
                                >
                                    {course.description}
                                </Typography>
                                <Box sx={{ mt: 'auto', pt: 1, textAlign: { xs: 'center', md: 'left' } }}>
                                    <Button
                                        variant="contained"
                                        rel="noopener noreferrer"
                                        onClick={() => showModalForCourse(course)}
                                        disabled={course.enrolled}
                                        sx={{
                                            px: { xs: 5 },
                                            backgroundColor: organization.brand_color,
                                            color: getReadableTextColor(organization.brand_color),
                                            '&:hover': { backgroundColor: organization.brand_color, filter: 'brightness(0.9)' },
                                            border: '1px solid',
                                            borderColor: alpha(getReadableTextColor(organization.brand_color), 0.2),

                                        }}
                                    >
                                        {course.enrolled ? localeMessages['enrolled'] : localeMessages['enroll_now']}
                                    </Button>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                    )
                })}
                </Grid>
            ) : (
                <Box
                    sx={{
                        p: 3,
                        borderRadius: 2,
                        border: '1px dashed',
                        borderColor: 'border.main',
                        backgroundColor: 'background.box',
                    }}
                >
                    <Typography variant="body1" sx={{ fontWeight: 500, mb: 0.5 }}>
                        {localeMessages['no_courses_available']}
                    </Typography>
                </Box>
            )}
        </Box>

        {newsletters.length > 0 && (
            <NewsletterSubscriptionForm
                newsletters={newsletters}
                subscribeApiUrl={newsletterSubscribeApiUrl}
                localeMessages={localeMessages}
                brandColor={organization.brand_color}
            />
        )}

        <Dialog open={displayModal} onClose={() => setDisplayModal(false)} fullWidth maxWidth="sm">
            {modalContent}
        </Dialog>

    </Layout></ThemeProvider>;
}

render({children: <Organization />});
