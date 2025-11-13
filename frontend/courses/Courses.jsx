import 'vite/modulepreload-polyfill'
import { useState, useEffect, use } from 'react'
import { Grid, Box, FormControlLabel, Link, Typography, Button, Dialog, Paper, RadioGroup, Radio, Switch, TableContainer, Table, TableHead, TableRow,TableBody, TableCell } from '@mui/material'
import Base from '../src/components/Base.jsx'
import CourseForm from './components/CourseForm.jsx';
import FilterListIcon from '@mui/icons-material/FilterList';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import render from '../src/render.jsx';
import { getCookie } from '../src/utils.js';
import EnableCourseSwitchPopup from './components/EnableCourseSwitchPopup.jsx';
import DeleteCoursePopup from './components/DeleteCoursePopup.jsx';
import FilterForm from './components/FilterForm.jsx';


function Courses() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogContent, setDialogContent] = useState(null)
  const [courses, setCourses] = useState([])
  const [organizationId, setOrganizationId] = useState(null);
  const [queryParameters, setQueryParameters] = useState("");
  const apiBaseUrl = localStorage.getItem('apiBaseUrl');

  const renderCourses = () => {
    if (!organizationId) {
      return;
    }
    fetch(`${apiBaseUrl}/organizations/${organizationId}/courses${queryParameters}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
        })
      .then(response => response.json())
      .then(data => setCourses(data.courses))
      .catch(error => console.error('Error fetching courses:', error));
  };

  useEffect(() => {
    renderCourses();
  }, [queryParameters]);

  useEffect(() => {
    setQueryParameters("");
    renderCourses();
  }, [organizationId]);

  const updateCourseState = (data) => {
    let course = courses.find(c => c.id === data.id);
    if (course) {
      course.enabled = data.enabled;
      setCourses([...courses]);
    }
  }

  const showEnableCoursePopup = (courseId, action, courseTitle) =>  (event) => {
    console.log(`${action} course with ID:`, courseId);
    console.log('Event:', event.target.checked);
    setDialogContent(<Grid sx={{ p: 2 }}>
      <EnableCourseSwitchPopup courseId={courseId} action={action} courseTitle={courseTitle} handleClose={() => setDialogOpen(false)} handleSuccess={updateCourseState}/>
    </Grid>);
    setDialogOpen(true);
  }

  const handleCourseCreated = (data) => {
    console.log('Course created successfully:', data);
    setCourses([...courses, data]);
    setDialogOpen(false);
  };

  const handleCourseCreationFailed = (error) => {
    console.error('Course creation failed:', error);
  };

  const showEditCourseDialog = (course) => {
    setDialogContent(<CourseForm
      successCallback={(data) => {
        const index = courses.findIndex(item => item.id === course.id);
        courses[index] = data;
        setCourses([...courses]);
        setDialogOpen(false);
      }}
      failureCallback={(error) => {
        console.error('Course update failed:', error);
      }}
      cancelCallback={() => setDialogOpen(false)}
      activeOrganizationId={organizationId}
      createMode={false}
      courseId={course.id}
    />);
    setDialogOpen(true);
  }

  return (
    <Base
      breadCrumbList={[{label: 'Course Management', href: '#'}]}
      bottomDrawerParams={{
        icon: <FilterListIcon />,
        children: <FilterForm onStatusChange={(params) => setQueryParameters(params)} />
      }}
      organizationIdRefreshCallback={setOrganizationId}
    >
      <Grid size={{xs: 12, md: 9}} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300 }}>
        <Button variant="outlined" startIcon={<AddIcon />} sx={{ marginBottom: 2 }} onClick={() => {
          setDialogContent(<CourseForm
            successCallback={handleCourseCreated}
            failureCallback={handleCourseCreationFailed}
            cancelCallback={() => setDialogOpen(false)}
            activeOrganizationId={organizationId}
            createMode={true}
          />);
          setDialogOpen(true);}}>Add a Course</Button>
        <TableContainer component={Paper}>
          <Table sx={{ width: "100%" }} aria-label="Courses">
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Slug</TableCell>
                <TableCell>Enabled</TableCell>
                <TableCell align='right'>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {courses.length > 0 && courses.map((course) => (
                <TableRow
                  key={course.id}
                  sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                >
                  <TableCell component="th" scope="row">
                    <Link href={`/courses/${course.id}`}>{course.title}</Link>
                  </TableCell>
                  <TableCell>{course.slug}</TableCell>
                  <TableCell>
                    <Switch
                      checked={course.enabled}
                      onChange={showEnableCoursePopup(course.id, course.enabled ? 'disable' : 'enable', course.title)}
                      slotProps={{ input: { 'aria-label': course.enabled ? 'Disable Course' : 'Enable Course' } }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Button size="small" sx={{ color: 'secondary.main', }} aria-label={`Edit ${course.title}`} onClick={() => {
                      showEditCourseDialog(course);}}>Edit</Button>
                    <Button size="small" sx={{ color: 'secondary.main', }} aria-label={`Delete ${course.title}`} onClick={() => {
                      setDialogContent(<DeleteCoursePopup courseId={course.id} courseTitle={course.title} handleClose={() => setDialogOpen(false)} handleSuccess={() => {
                        const index = courses.findIndex(item => item.id === course.id);
                        setCourses(courses.filter((_, i) => i !== index));
                    }} />);
                    setDialogOpen(true);
                  }}><DeleteOutlineIcon fontSize="small" /></Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        </Box>
      </Grid>
      <Grid display={{xs: "none", md: "block"}} size={{ md: 3 }} p={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300, position: 'sticky', top: 80 }}>
          <FilterForm onStatusChange={(params) => setQueryParameters(params)} />
        </Box>
      </Grid>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>

    </Base>
  )
}

render({children: <Courses />});
