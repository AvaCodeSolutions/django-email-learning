import 'vite/modulepreload-polyfill'
import { useState, useEffect } from 'react'
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Link from '@mui/material/Link';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Dialog from '@mui/material/Dialog';
import LinearProgress from '@mui/material/LinearProgress';
import Paper from '@mui/material/Paper';
import Switch from '@mui/material/Switch';
import TableContainer from '@mui/material/TableContainer';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import Base from '../../src/components/Base.jsx'
import SchoolIcon from '@mui/icons-material/School';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import LockIcon from '@mui/icons-material/Lock';
import render, { useAppContext } from '../../src/render.jsx';
import { getCookie } from '../../src/utils.js';
import { lazy, Suspense } from "react";

const CourseForm = lazy(() => import("./components/CourseForm.jsx"));
const EnableCourseSwitchPopup = lazy(() => import("./components/EnableCourseSwitchPopup.jsx"));
const DeleteCoursePopup = lazy(() => import("./components/DeleteCoursePopup.jsx"));



function Courses() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogContent, setDialogContent] = useState(null)
  const [courses, setCourses] = useState([])
  const [organizationId, setOrganizationId] = useState(null);
  const [queryParameters, setQueryParameters] = useState("");
  const { direction, localeMessages, apiBaseUrl, platformBaseUrl, userRole, languageOptions = [] } = useAppContext();
  const [coursesAreLoaded, setCoursesAreLoaded] = useState(false);

  const getLanguageLabel = (languageCode) => {
    return languageOptions.find((languageOption) => languageOption.value === languageCode)?.label || languageCode;
  }

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
      .then(data => {
        setCourses(data.courses);
        setCoursesAreLoaded(true);
      })
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
      <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><EnableCourseSwitchPopup courseId={courseId} action={action} courseTitle={courseTitle} handleClose={() => setDialogOpen(false)} handleSuccess={updateCourseState}/></Suspense>
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
    setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><CourseForm
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
    /></Suspense>);
    setDialogOpen(true);
  }

  return (
    <Base
      breadCrumbList={[{label: localeMessages.course_management, href: '#'}]}
      organizationIdRefreshCallback={setOrganizationId}
    >
      <Grid size={{xs: 12}} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'border.main', backgroundColor: 'background.box', borderRadius: 2, minHeight: 300 }}>
        {userRole !== 'viewer' && <Button variant="contained" startIcon={<SchoolIcon sx={{ marginLeft: direction === 'rtl' ? 1 : 0 }} />} sx={{ marginBottom: 2 }} onClick={() => {
          setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><CourseForm
            successCallback={handleCourseCreated}
            failureCallback={handleCourseCreationFailed}
            cancelCallback={() => setDialogOpen(false)}
            activeOrganizationId={organizationId}
            createMode={true}
          /></Suspense>);
          setDialogOpen(true);}}>{localeMessages["add_course"]}</Button>}
        {coursesAreLoaded ? <TableContainer component={Paper}>
          <Table aria-label={localeMessages["courses"]}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["title"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["course_language"]}</TableCell>
                <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["total_enrollments"]}</TableCell>
                <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>{localeMessages["enabled"]}</TableCell>
                {userRole !== 'viewer' && <TableCell align={direction === 'rtl' ? 'left' : 'right'}>{localeMessages["actions"]}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {courses.length > 0 && courses.map((course) => (
                <TableRow key={course.id}>
                  <TableCell component="th" scope="row" sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>
                    <Link href={`${platformBaseUrl}/courses/${course.id}`} color='secondary.dark'>{course.title}</Link>{course.is_public ? "" : <Chip icon={<LockIcon fontSize="small" />} label={localeMessages["private"]} size="small" sx={{ ml: 1 }} />}
                  </TableCell>
                  <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: direction === 'rtl' ? 'right' : 'left' }}>{getLanguageLabel(course.language)}</TableCell>
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
                      setDialogContent(<Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><DeleteCoursePopup courseId={course.id} courseTitle={course.title} handleClose={() => setDialogOpen(false)} handleSuccess={() => {
                        const index = courses.findIndex(item => item.id === course.id);
                        setCourses(courses.filter((_, i) => i !== index));
                    }} /></Suspense>);
                    setDialogOpen(true);
                  }}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>}
                </TableRow>
              ))}
              {courses.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={userRole !== 'viewer' ? 5 : 4}
                    sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}
                  >
                    {localeMessages["no_courses_found"] || "No courses found."}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer> : <LinearProgress />}
        </Box>
      </Grid>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>

    </Base>
  )
}

render({children: <Courses />});
