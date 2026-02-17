import { useState, useEffect } from 'react'
import render from '../../src/render.jsx';
import Layout from '../components/Layout.jsx';
import EnrollmentForm from '../components/EnrollmentForm.jsx';
import { Alert, Box, Button, CardMedia, Dialog, Grid, Typography } from '@mui/material';
import { useAppContext } from '../../src/render.jsx';


function Organization() {

    const [displayModal, setDisplayModal] = useState(false);
    const [modalContent, setModalContent] = useState(null);
    const [courses, setCourses] = useState([]);

    const { organization, enrollApiUrl, localeMessages } = useAppContext();

    useEffect(() => {
        for (let course of organization.courses) {
            course.enrolled = false;
        }
        setCourses(organization.courses);
    }, []);

    const showModalForCourse = (course) => {
        // Logic to show modal for specific course
        setModalContent(<EnrollmentForm course_title={course.title} course_slug={course.slug} organization_id={organization.id} endpoint={enrollApiUrl} onCancle={() => {setDisplayModal(false); setModalContent(null);}} onComplete={() => completeEnrollment(course)} />);
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


    return <Layout>
        { organization.logo_url &&
            <img src={ organization.logo_url } alt={`${organization.name} Logo`} style={{ maxWidth: '200px', height: 'auto' }} />
        }
        <Typography variant="h1">{ organization.name }</Typography>
        <Typography variant="body1" dangerouslySetInnerHTML={{ __html: organization.description }} />
        <Box my={4}>
            <Typography variant="h2">{localeMessages['courses']}:</Typography>
            { organization.courses.length > 0 ? (
                <Grid container columnSpacing={2} rowSpacing={6} alignItems="stretch">
                { courses.map((course) => (
                    <Grid size={{ xs: 12, md: 6 }} key={course.id} display="flex" >
                    <Box key={course.id} p={2} border={1} borderRadius={2} sx={{ height: '100%', width: '100%'}}>
                    <CardMedia
                    component={course.image ? "img" : "div"} // Swaps element type
                    image={course.image}
                    sx={{
                        height: 360,

                        backgroundColor: 'grey.300', // Shows if component is "div" or image is transparent
                        objectFit: 'cover',
                    }}
                    >

                    </CardMedia>

                        <Typography variant="h3" sx={{ pt: 2 }}>{course.title}</Typography>
                        <Button variant="contained" color="primary" rel="noopener noreferrer" sx={{ mt: 1, mb: 2 }} onClick={() => showModalForCourse(course)} disabled={course.enrolled}>
                            {localeMessages['enroll_now']}
                        </Button>
                        <Typography variant="body2" dangerouslySetInnerHTML={{ __html: course.description }} />
                        { course.enrolled && <Alert severity="success" sx={{ mt: 2 }}>{localeMessages['enrollment_success']}</Alert> }
                    </Box>
                    </Grid>
                ))}
                </Grid>
            ) : (
                <Typography variant="body2">{localeMessages['no_courses_available']}</Typography>
            )}
        </Box>

        <Dialog open={displayModal} onClose={() => setDisplayModal(false)}>
            {modalContent}
        </Dialog>

    </Layout>;
}

render({children: <Organization />});
