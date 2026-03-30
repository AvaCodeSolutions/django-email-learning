import { useState } from 'react'
import render from '../../src/render.jsx';
import Layout from '../components/Layout.jsx';
import EnrollmentForm from '../components/EnrollmentForm.jsx';
import { Box, Button, Card, Chip, Dialog, List, ListItem, ListItemIcon, ListItemText, Stack, Typography } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { alpha, ThemeProvider } from '@mui/material/styles';
import { useAppContext } from '../../src/render.jsx';
import { lightTheme } from '../../src/theme/themes';


function Course() {

    const [displayModal, setDisplayModal] = useState(false);
    const [modalContent, setModalContent] = useState(null);
    const [enrolled, setEnrolled] = useState(false);

    const { course, organization, enrollApiUrl, localeMessages, csrfToken } = useAppContext();

    const courseDirection = course.is_rtl ? 'rtl' : 'ltr';

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
                csrfToken={csrfToken}
            />
        );
        setDisplayModal(true);
    }

    const completeEnrollment = () => {
        setDisplayModal(false);
        setModalContent(null);
        setEnrolled(true);
    }

    return <ThemeProvider theme={lightTheme}><Layout>
        {/* Course Header with Image and Title */}
        <Box
            sx={{
                mb: 4,
                borderRadius: 2,
                overflow: 'hidden',
                backgroundColor: 'background.dark',
                direction: courseDirection,
            }}
        >
            {course.image && (
                <Box
                    component="img"
                    src={course.image}
                    alt={course.title}
                    sx={{
                        width: '100%',
                        height: 'auto',
                        aspectRatio: '16 / 9',
                        objectFit: 'cover',
                        display: 'block',
                    }}
                />
            )}
        </Box>

        {/* Course Info Section */}
        <Box
            sx={{
                p: { xs: 2, md: 3 },
                mb: 4,
                borderRadius: 2,
                backgroundColor: (theme) => theme.palette.mode === 'light'
                    ? alpha(theme.palette.primary.main, 0.05)
                    : alpha(theme.palette.common.white, 0.04),
                direction: courseDirection,
            }}
        >
            <Stack spacing={2}>
                <Box>
                    <Typography variant="h1" sx={{ mb: 1 }}>{course.title}</Typography>
                    <Stack direction={courseDirection === 'rtl' ? 'row-reverse' : 'row'} spacing={1} alignItems="center">
                        <Chip
                            label={course.language}
                            size="small"
                            variant="outlined"
                        />
                    </Stack>
                </Box>

                {course.description && (
                    <Typography
                        variant="body1"
                        sx={{ color: 'text.secondary' }}
                        dangerouslySetInnerHTML={{ __html: course.description }}
                    />
                )}

                {/* Organization Info */}
                <Box
                    sx={{
                        p: 2,
                        borderRadius: 1.5,
                        backgroundColor: "white",
                        mt: 2,
                        direction: courseDirection,
                    }}
                >
                    <Stack spacing={1.5} direction={courseDirection === 'rtl' ? 'row-reverse' : 'row'} alignItems="center">
                        {organization.logo_url && (
                            <Box
                                component="img"
                                src={organization.logo_url}
                                alt={`${organization.name} Logo`}
                                sx={{
                                    maxWidth: 120,
                                    height: 'auto',
                                    borderRadius: 1,
                                }}
                            />
                        )}
                        <Stack spacing={0.5} sx={{ flex: 1, direction: courseDirection }}>
                            <Typography variant="body2" sx={{ fontWeight: 500, color: 'text.secondary' }}>
                                {localeMessages['provided_by'].replace('ORGANIZATION_NAME', organization.name)}
                            </Typography>
                            {organization.description && (
                                <Typography
                                    variant="body2"
                                    sx={{ color: 'text.secondary', fontSize: '0.875rem' }}
                                    dangerouslySetInnerHTML={{ __html: organization.description }}
                                />
                            )}
                        </Stack>
                    </Stack>
                </Box>
            </Stack>
        </Box>

        {/* Topics/Lessons Section */}
        {course.lessons && course.lessons.length > 0 && (
            <Box my={4}>
                <Typography variant="h2" sx={{ mb: 2, direction: courseDirection }}>
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
                                            color: 'primary.main',
                                            fontSize: '1.5rem',
                                        }}
                                    />
                                </ListItemIcon>
                                <ListItemText
                                    primary={lesson}
                                    primaryTypographyProps={{
                                        variant: 'body2',
                                        sx: {
                                            textAlign: courseDirection === 'rtl' ? 'right' : 'left',
                                        }
                                    }}
                                />
                            </ListItem>
                        ))}
                    </List>
                </Card>
            </Box>
        )}

        {/* Enrollment Section */}
        <Box
            sx={{
                p: { xs: 2, md: 3 },
                borderRadius: 2,
                backgroundColor: (theme) => theme.palette.mode === 'light'
                    ? alpha(theme.palette.primary.main, 0.08)
                    : alpha(theme.palette.primary.main, 0.15),
                textAlign: courseDirection === 'rtl' ? 'right' : 'left',
                direction: courseDirection,
            }}
        >
            <Stack spacing={2} alignItems={courseDirection === 'rtl' ? 'flex-end' : 'flex-start'}>
                <Typography variant="h3">
                    {localeMessages['ready_to_learn'] || 'Ready to Get Started?'}
                </Typography>
                <Typography variant="body1" sx={{ color: 'text.secondary' }}>
                    {localeMessages['enrollment_intro'] || 'Enroll now to begin your learning journey with this course.'}
                </Typography>
                <Box sx={{ pt: 1 }}>
                    {enrolled ? (
                        <Chip
                            label={localeMessages['enrollment_success']}
                            sx={(theme) => ({
                                backgroundColor: alpha(theme.palette.success.main, 0.15),
                                color: theme.palette.success.main,
                            })}
                        />
                    ) : (
                        <Button
                            variant="contained"
                            color="primary"
                            size="large"
                            onClick={showEnrollmentModal}
                        >
                            {localeMessages['enroll_now']}
                        </Button>
                    )}
                </Box>
            </Stack>
        </Box>

        <Dialog open={displayModal} onClose={() => setDisplayModal(false)} fullWidth maxWidth="sm">
            {modalContent}
        </Dialog>

    </Layout></ThemeProvider>;
}

render({ children: <Course /> });
