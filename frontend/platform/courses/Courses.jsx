import 'vite/modulepreload-polyfill'
import { useState, useEffect } from 'react'
import { Grid, Box, Link, Button, IconButton, Dialog, Paper, Switch, TableContainer, Table, TableHead, TableRow,TableBody, TableCell } from '@mui/material'
import Base from '../../src/components/Base.jsx'
import CourseForm from './components/CourseForm.jsx';
import FilterListIcon from '@mui/icons-material/FilterList';
import SchoolIcon from '@mui/icons-material/School';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import render from '../../src/render.jsx';
import { getCookie } from '../../src/utils.js';
import EnableCourseSwitchPopup from './components/EnableCourseSwitchPopup.jsx';
import DeleteCoursePopup from './components/DeleteCoursePopup.jsx';
import FilterForm from './components/FilterForm.jsx';


function Courses() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogContent, setDialogContent] = useState(null)
  const [courses, setCourses] = useState([])
  const [organizationId, setOrganizationId] = useState(null);
  const [queryParameters, setQueryParameters] = useState("");
  const userRole = localStorage.getItem('userRole');
  const apiBaseUrl = localStorage.getItem('apiBaseUrl');
  const platformBaseUrl = localStorage.getItem('platformBaseUrl');

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
      breadCrumbList={[{label: localeMessages["course_management"], href: '#'}]}
      bottomDrawerParams={{
        icon: <FilterListIcon />,
        children: <FilterForm onStatusChange={(params) => setQueryParameters(params)} />
      }}
      organizationIdRefreshCallback={setOrganizationId}
    >
      <Grid size={{xs: 12, md: 9}} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'border.main', backgroundColor: 'background.main', borderRadius: 1, minHeight: 300 }}>
        {userRole !== 'viewer' && <Button variant="contained" startIcon={<SchoolIcon sx={{ marginLeft: direction === 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2 }} onClick={() => {
          setDialogContent(<CourseForm
            successCallback={handleCourseCreated}
            failureCallback={handleCourseCreationFailed}
            cancelCallback={() => setDialogOpen(false)}
            activeOrganizationId={organizationId}
            createMode={true}
          />);
          setDialogOpen(true);}}>{localeMessages["add_course"]}</Button>}
        <TableContainer component={Paper}>
          <Table sx={{ width: "100%" }} aria-label={localeMessages["courses"]}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["title"]}</TableCell>
                <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["total_enrollments"]}</TableCell>
                <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["enabled"]}</TableCell>
                {userRole !== 'viewer' && <TableCell align={direction === 'rtl' ? 'left' : 'right'}>{localeMessages["actions"]}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {courses.length > 0 && courses.map((course) => (
                <TableRow
                  key={course.id}
                  sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                >
                  <TableCell component="th" scope="row" sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>
                    <Link href={`${platformBaseUrl}/courses/${course.id}`} color='primary.dark'>{course.title}</Link>
                  </TableCell>
                  <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{course.enrollments_count.total}</TableCell>
                  <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>
                    <Switch
                      checked={course.enabled}
                      onChange={showEnableCoursePopup(course.id, course.enabled ? 'disable' : 'enable', course.title)}
                      slotProps={{ input: { 'aria-label': course.enabled ? 'Disable Course' : 'Enable Course' } }}
                      disabled={userRole === 'viewer'}
                    />
                  </TableCell>
                  {userRole !== 'viewer' && <TableCell align={direction === 'rtl' ? 'left' : 'right'}>
                    <IconButton onClick={() => {
                      showEditCourseDialog(course);}}><EditIcon fontSize="small" /></IconButton>
                    <IconButton aria-label={`Delete ${course.title}`} onClick={() => {
                      setDialogContent(<DeleteCoursePopup courseId={course.id} courseTitle={course.title} handleClose={() => setDialogOpen(false)} handleSuccess={() => {
                        const index = courses.findIndex(item => item.id === course.id);
                        setCourses(courses.filter((_, i) => i !== index));
                    }} />);
                    setDialogOpen(true);
                  }}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        </Box>
      </Grid>
      <Grid display={{xs: "none", md: "block"}} size={{ md: 3 }} p={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'border.main', borderRadius: 1, minHeight: 300, position: 'sticky', top: 80, backgroundColor: 'background.main' }}>
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
