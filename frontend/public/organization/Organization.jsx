import { useState, useEffect } from 'react'
import render from '../../src/render.jsx';
import Layout from '../components/Layout.jsx';
import EnrollmentForm from '../components/EnrollmentForm.jsx';
import { Box, Button, Card, CardContent, CardMedia, Chip, Dialog, Grid, Stack, Typography } from '@mui/material';
import LanguageIcon from '@mui/icons-material/Language';
import { alpha, ThemeProvider } from '@mui/material/styles';
import { useAppContext } from '../../src/render.jsx';
import { lightTheme } from '../../src/theme/themes';


function Organization() {

    const [displayModal, setDisplayModal] = useState(false);
    const [modalContent, setModalContent] = useState(null);
    const [courses, setCourses] = useState([]);

    const { organization, enrollApiUrl, localeMessages } = useAppContext();

    useEffect(() => {
        const initialCourses = (organization.courses || []).map((course) => ({ ...course, enrolled: false }));
        setCourses(initialCourses);
    }, []);

    const showModalForCourse = (course) => {
        // Logic to show modal for specific course
        setModalContent(<EnrollmentForm course_title={course.title} course_slug={course.slug} organization_id={organization.id} endpoint={enrollApiUrl} autoFocusEmail={true} onCancle={() => {setDisplayModal(false); setModalContent(null);}} onComplete={() => completeEnrollment(course)} />);
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
    }


    return <ThemeProvider theme={lightTheme}><Layout>
        <Box
            sx={{
                p: { xs: 2, md: 3 },
                mb: 4,
                borderRadius: 2,
                backgroundColor: (theme) => theme.palette.mode === 'light'
                    ? alpha(theme.palette.primary.main, 0.05)
                    : alpha(theme.palette.common.white, 0.04),
            }}
        >
            <Stack spacing={2}>
                { organization["logo_url"] &&
                    <Box>
                        <Box component="img" src={ organization["logo_url"] } alt={`${organization["name"]} Logo`} sx={{ maxWidth: 220, width: '100%', height: 'auto' }} />
                    </Box>
                }
                <Typography variant="h1" sx={{ mb: 0 }}>{ organization["name"] }</Typography>
                <Typography variant="body1" sx={{ color: 'text.secondary' }} dangerouslySetInnerHTML={{ __html: organization["description"] }} />
            </Stack>
        </Box>
        <Box my={4}>
            <Typography variant="h2" sx={{ mb: 2 }}>{localeMessages['courses']}</Typography>
            { courses.length > 0 ? (
                <Grid container columnSpacing={2} rowSpacing={3} alignItems="stretch">
                { courses.map((course) => {
                    const courseDirection = course.is_rtl ? 'rtl' : 'ltr';
                    return (
                    <Grid size={{ xs: 12, sm: 6, md: 4 }} key={course["id"]} display="flex" >
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
                                    transform: 'translateY(-2px)',
                                    borderColor: 'primary.main',
                                    boxShadow: (theme) => theme.palette.mode === 'dark'
                                        ? '0 8px 18px rgba(0,0,0,0.28)'
                                        : '0 8px 18px rgba(16,24,40,0.10)',
                                },
                            }}
                        >
                            <CardMedia
                                component={course["image"] ? "img" : "div"}
                                image={course["image"]}
                                sx={{
                                    aspectRatio: '16 / 9',
                                    backgroundColor: 'background.dark',
                                    objectFit: 'cover',
                                }}
                            />
                            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.25, flexGrow: 1, direction: course.is_rtl ? 'rtl' : 'ltr' }}>
                                <Box>
                                    <Typography variant="h3" sx={{ textAlign: courseDirection === 'rtl' ? 'right' : 'left' }}>{course["title"]}</Typography>
                                    <Stack direction={courseDirection === 'rtl' ? 'rtl' : 'ltr'} alignItems="center" spacing={0.5} sx={{ mt: 0.25 }}>
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
                                    dangerouslySetInnerHTML={{ __html: course.description }}
                                />
                                <Box sx={{ mt: 'auto', pt: 1 }}>
                                    {course.enrolled && (<>
                                        <Chip
                                            label={localeMessages['enrollment_success']}
                                            size="small"
                                            sx={(theme) => ({ mb: 1., backgroundColor: alpha(theme.palette.success.main, 0.15), color: theme.palette.success.main })}
                                        /><br /></>
                                    )}
                                    <Button
                                        variant="contained"
                                        color="secondary"
                                        rel="noopener noreferrer"
                                        onClick={() => showModalForCourse(course)}
                                        disabled={course.enrolled}
                                    >
                                        {localeMessages['enroll_now']}
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

        <Dialog open={displayModal} onClose={() => setDisplayModal(false)} fullWidth maxWidth="sm">
            {modalContent}
        </Dialog>

    </Layout></ThemeProvider>;
}

render({children: <Organization />});
