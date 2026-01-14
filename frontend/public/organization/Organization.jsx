import { useState } from 'react'
import render from '../../src/render.jsx';
import Layout from '../components/Layout.jsx';
import EnrollmentForm from '../components/EnrollmentForm.jsx';
import { Box, Button, Dialog, Grid, Typography } from '@mui/material';


function Organization() {

    const [displayModal, setDisplayModal] = useState(false);
    const [modalContent, setModalContent] = useState(null);

    const showModalForCourse = (course) => {
        // Logic to show modal for specific course
        setModalContent(<EnrollmentForm course_title={course.title} course_slug={course.slug} onCancel={() => {setDisplayModal(false); setModalContent(null);}} />);
        setDisplayModal(true);
    }


    return <Layout>
        { organization.logo_url &&
            <img src={ organization.logo_url } alt={`${organization.name} Logo`} style={{ maxWidth: '200px', height: 'auto' }} />
        }
        <Typography variant="h1">{ organization.name }</Typography>
        <Typography variant="body1" dangerouslySetInnerHTML={{ __html: organization.description }} />
        <Box my={4}>
            <Typography variant="h2">Courses:</Typography>
            { organization.courses.length > 0 ? (
                <Grid container spacing={2}>
                { organization.courses.map((course) => (
                    <Grid size={{ xs: 12, md: 6 }} key={course.id}>
                    <Box key={course.id} mb={2} p={2} border={1} borderRadius={2} sx={{ minHeight: '100%' }}>
                        <Typography variant="h3">{course.title}</Typography>
                        <Button variant="contained" color="primary" rel="noopener noreferrer" sx={{ mt: 1, mb: 2 }} onClick={() => showModalForCourse(course)}>
                            Enroll Now
                        </Button>
                        <Typography variant="body2" dangerouslySetInnerHTML={{ __html: course.description }} />
                    </Box>
                    </Grid>
                ))}
                </Grid>
            ) : (
                <Typography variant="body2">No courses available.</Typography>
            )}
        </Box>

        <Dialog open={displayModal} onClose={() => setDisplayModal(false)}>
            {modalContent}
        </Dialog>

    </Layout>;
}

render({children: <Organization />});
