import Base from '../../src/components/Base.jsx'
import EmptyTableState from '../../src/components/EmptyTableState.jsx'
import { Avatar, InputBase, IconButton, Box, Button, Chip, Dialog, FormControl, Grid, InputLabel, LinearProgress, MenuItem, Pagination, Paper, Select, TableContainer, Table, TableBody, TableHead, TableCell, TableRow, Tooltip, Typography } from '@mui/material'
import { Timeline, TimelineItem, TimelineContent, TimelineOppositeContent, TimelineSeparator, TimelineConnector, TimelineDot } from '@mui/lab'
import { useState, useEffect, useRef } from 'react'
import FilterListOffIcon from '@mui/icons-material/FilterListOff';
import AppRegistrationIcon from '@mui/icons-material/AppRegistration';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import LibraryBooksIcon from '@mui/icons-material/LibraryBooks';
import BallotIcon from '@mui/icons-material/Ballot';
import AssignmentIcon from '@mui/icons-material/Assignment';
import AssignmentIndIcon from '@mui/icons-material/AssignmentInd';
import AssignmentReturnedIcon from '@mui/icons-material/AssignmentReturned';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import SearchIcon from '@mui/icons-material/Search';
import SchoolIcon from '@mui/icons-material/School';
import BackspaceIcon from '@mui/icons-material/Backspace';
import render, { useAppContext } from '../../src/render.jsx';
import { lazy, Suspense } from "react";
import apiClient from '../../src/apiClient.js';

const EnrollentList = lazy(() => import("./components/EnrollmentList.jsx"));


const ENROLLMENT_STATUSES = ['active', 'completed', 'deactivated', 'canceled', 'inactive'];

function Learners(initialQs="") {

  const [organizationId, setOrganizationId] = useState(null);
  const { localeMessages, direction, apiBaseUrl } = useAppContext();
  const [learners, setLearners] = useState([]);
  const searcchInputRef = useRef(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogContent, setDialogContent] = useState(null);
  const [showPagination, setShowPagination] = useState(false);
  const pageSize = 20;
  const [pagesCount, setPagesCount] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [courses, setCourses] = useState([]);

  // Read initial filter values from URL query params
  const urlParams = new URLSearchParams(window.location.search);
  const [courseFilter, setCourseFilter] = useState(urlParams.get('course_id') || '');
  const [statusFilter, setStatusFilter] = useState(urlParams.get('status') || '');
  const [searchQs, setSearchQs] = useState('');

  const buildQs = () => {
    const parts = [];
    if (courseFilter) parts.push(`course_id=${encodeURIComponent(courseFilter)}`);
    if (statusFilter) parts.push(`status=${encodeURIComponent(statusFilter)}`);
    if (searchQs) parts.push(searchQs);
    return parts.join('&');
  };

  const qs = buildQs();

  const eventMap = {
    'registered': {icon: <AppRegistrationIcon sx={{ color: 'white' }} />, color: "#00bcd4", title: localeMessages["learner_registered"]},
    'verified': {icon: <HowToRegIcon />, color: "#66bb6a", title: localeMessages["learner_verified"]},
    'content_sent_lesson': {icon: <LibraryBooksIcon />, color: "#00acc1", title: localeMessages["lesson_sent"]},
    'content_sent_quiz': {icon: <BallotIcon />, color: "#26a69a", title: localeMessages["quiz_sent"]},
    'content_sent_assignment': {icon: <AssignmentIcon />, color: "#336eb7", title: localeMessages["assignment_sent"]},
    'quiz_submitted': {icon: <AssignmentReturnedIcon />, color: "#26a69a", title: localeMessages["quiz_submitted"]},
    'course_completed': {icon: <SchoolIcon />, color: "#0097a7", title: localeMessages["course_completed"]},
    'deactivated': {icon: <BackspaceIcon />, color: "#b71c1c", title: localeMessages["learner_deactivated"]},
    'reminder_sent': {icon: <NotificationsActiveIcon />, color: "#ae4ad6", title: localeMessages["reminder_sent"]},
    'assignment_submitted': {icon: <AssignmentReturnedIcon />, color: "#23bca8", title: localeMessages["assignment_submitted"]},
    'assignment_reviewed': {icon: <AssignmentIndIcon />, color: "#336eb7", title: localeMessages["assignment_reviewed"]},
  };


  const showEnrollmentStatus = (enrollmentId) => {
    setDialogOpen(true);
    setDialogContent(<LinearProgress sx={{ m: 10 }} />);
    apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/enrollments/${enrollmentId}/`)
    .then(data => {
      setDialogContent(
        <Box>
          <Box sx={{ px: 3, pt: 3, pb: 2, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar src={data.learner.photo || undefined} sx={(theme) => ({ width: 44, height: 44, fontSize: '1.1rem', fontWeight: 700, color: '#fff', background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.deepPurple?.[400] ?? theme.palette.secondary.main} 100%)` })}>
              {(data.learner.email?.[0] || '?').toUpperCase()}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data.learner.email}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data.course.title}</Typography>
            </Box>
            <Chip label={`ID: ${data.id}`} size="small" variant="outlined" sx={{ flexShrink: 0, fontFamily: 'monospace' }} />
          </Box>
          <Box sx={{ px: 2 }}>
          <Timeline>
            {data.events.map((event, index) => (
            <TimelineItem key={index}>
              <TimelineOppositeContent
                sx={{ m: 'auto 0' }}
                align="right"
                variant="body2"
                color="text.secondary"
              >
                {event.timestamp.replace('T', ' ').replace('Z', '')}
              </TimelineOppositeContent>
              <TimelineSeparator>
                <TimelineConnector />
                <TimelineDot sx={{backgroundColor: event.type === "content_sent" ? eventMap["content_sent_"+event.event_data.course_content_type].color : eventMap[event.type].color }}>
                  { event.type=="content_sent" ? eventMap["content_sent_"+event.event_data.course_content_type].icon : eventMap[event.type].icon }
                </TimelineDot>
                <TimelineConnector />
              </TimelineSeparator>
              <TimelineContent sx={{ py: '12px', px: 2, textAlign: direction === 'rtl' ? 'right' : 'left' }} dir={direction}>
                <Typography variant="h6" component="span">
                  { event.type === "content_sent" ? eventMap["content_sent_"+event.event_data.course_content_type].title : eventMap[event.type].title }
                </Typography>
                { event.type === "quiz_submitted" && <>
                  <Box><Typography>{localeMessages["score"]}: {event.event_data.score}</Typography></Box>
                  <Box><Typography sx={{ display: 'flex', alignItems: 'center' }}>{ event.event_data.is_practice ? <Chip label={localeMessages["practice_attempt"]} size="small"/> : <>{localeMessages["result"]}: {event.event_data.is_passed ? <>{localeMessages["passed"]}<CheckCircleIcon sx={{color: "#4caf50", marginX: "4px"}} /></> : <> {localeMessages["failed"]}<CancelIcon sx={{color: "#f44336", marginX: "4px"}} /></>}</>}</Typography></Box>
                </>}
                { event.type === "assignment_reviewed" && <>
                  <Box><Typography>{localeMessages["result"]}: {event.event_data.review_result === "approved" ? <><Typography component="span" sx={{color: "#4caf50"}}>{localeMessages["approved"]}</Typography><CheckCircleIcon sx={{color: "#4caf50", marginX: "4px"}} /></> : event.event_data.review_result === "rejected" ? <><Typography component="span" sx={{color: "#f44336"}}>{localeMessages["rejected"]}</Typography><CancelIcon sx={{color: "#f44336", marginX: "4px"}} /></> : <Typography component="span" sx={{color: "#ff9800"}}>{localeMessages["requesting_changes"]}</Typography>}</Typography></Box>
                  <Box><Typography>{localeMessages["reviewed_by"]}: {event.event_data.reviewed_by}</Typography></Box>
                </>}
                { event.type === "assignment_submitted" && <>
                  <Box><Typography>{localeMessages["assignment_title"]}: {event.event_data.assignment_title}</Typography></Box>
                </>}
                { event.type === "content_sent" && <>
                  <Box><Typography>{event.event_data.course_content_title}</Typography></Box>
                </>}
                { event.type === "deactivated" && <>
                  <Box><Typography>{localeMessages["reason"]}: {event.event_data.reason}</Typography></Box>
                </>}
                { event.type === "reminder_sent" && <>
                  <Box><Typography>{localeMessages["quiz_title"]}: {event.event_data.content_title}</Typography></Box>
                </>}
              </TimelineContent>
            </TimelineItem>
            ))}
          </Timeline>
          </Box>
        </Box>
      );

    })
    .catch(error => {
      console.error('Error fetching enrollment details:', error);
    });

  }

  const reloadLearners = () => {

    apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/learners/?${qs}&page_size=${pageSize}&page=${currentPage}`)
    .then(data => {
      setShowPagination(data.page != 1 || data.has_more);
      setPagesCount(Math.ceil(data.total_count / pageSize));
      setLearners(data.items.map(learner => ({
        id: learner.id,
        email: learner.email,
        photo: learner.photo || null,
        enrollmentsCount: learner.enrollments_count || { total: 0, completed: 0 },
        enrollmentStatus: learner.enrollment_status || null,
        enrollmentProgress: learner.enrollment_progress ?? null,
        enrollments: [],
        state: 0, // 0: not loaded, 1: loading, 2: loaded
      })));
    })
    .catch(error => {
      console.error('Error fetching learners:', error);
    });
  }

  useEffect(() => {
    if (!organizationId) {
      return;
    }
    reloadLearners();
  }, [organizationId, qs, currentPage]);

  useEffect(() => {
    if (!organizationId) return;
    apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/courses/`)
      .then(data => setCourses(data.courses || []))
      .catch(error => console.error('Error fetching courses:', error));
  }, [organizationId]);

  const loadEnrollments = (learner) => {
    if (learner.state === 2) {
      return Promise.resolve(learner.enrollments);
    }

    setLearners((prevLearners) => prevLearners.map((item) => (
      item.id === learner.id ? { ...item, state: 1 } : item
    )));

    return apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/learners/${learner.id}`)
    .then(data => {
      setLearners((prevLearners) => prevLearners.map((item) => (
        item.id === learner.id ? { ...item, enrollments: data.enrollments, state: 2 } : item
      )));
      return data.enrollments;
    })
    .catch(error => {
      console.error('Error fetching enrollments for learner:', error);
      setLearners((prevLearners) => prevLearners.map((item) => (
        item.id === learner.id ? { ...item, state: 0 } : item
      )));
      return [];
    });
  }

  const showLearnerEnrollments = (learner) => {
    setDialogOpen(true);
    setDialogContent(<LinearProgress sx={{ m: 10 }} />);

    const renderEnrollmentList = (enrollments) => {
      setDialogContent(
        <Box>
          <Box sx={{ px: 3, pt: 3, pb: 2, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar src={learner.photo || undefined} sx={(theme) => ({ width: 44, height: 44, fontSize: '1.1rem', fontWeight: 700, color: '#fff', background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.deepPurple?.[400] ?? theme.palette.secondary.main} 100%)` })}>
              {(learner.email?.[0] || '?').toUpperCase()}
            </Avatar>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{learner.email}</Typography>
          </Box>
          <Box sx={{ p: 2 }}>
          <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
            { enrollments && <EnrollentList enrollments={enrollments} selectHandler={showEnrollmentStatus} /> }
          </Suspense>
          </Box>
        </Box>
      );
    };

    if (learner.state === 2) {
      renderEnrollmentList(learner.enrollments);
      return;
    }

    loadEnrollments(learner).then((enrollments) => {
      renderEnrollmentList(enrollments);
    });
  }

  const search = () => {
    setSearchQs(`search=${encodeURIComponent(searcchInputRef.current.value)}`);
    setCurrentPage(1);
  };

  const handleCourseFilterChange = (e) => {
    setCourseFilter(e.target.value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (e) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  const resetFilters = () => {
    setCourseFilter('');
    setStatusFilter('');
    setSearchQs('');
    if (searcchInputRef.current) searcchInputRef.current.value = '';
    setCurrentPage(1);
  };

  const isFiltered = courseFilter || statusFilter || searchQs;

  return (
    <Base
          breadCrumbList={[{label: localeMessages["learners"], href: '#'}]}
          organizationIdRefreshCallback={setOrganizationId}
        >
      <Grid size={{xs: 12}} sx={{ py: 2, pl: 2 }}>
        <Box sx={{ p: 2, marginBottom: 2, border: '1px solid', borderColor: 'border.main', borderRadius: 2, minHeight: 300, backgroundColor: 'background.box' }}>

          {/* Search + filter bar */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2, alignItems: 'center' }}>
            <Paper sx={{ p: '2px 4px', display: 'flex', alignItems: 'center', minWidth: 260 }}>
              <InputBase
                sx={{ px: 1, flex: 1 }}
                placeholder={localeMessages["search_learners"]}
                inputRef={searcchInputRef}
                onKeyDown={(e) => { if (e.key === 'Enter') { search(); } }}
              />
              <IconButton type="button" sx={{ p: '10px' }} aria-label="search" onClick={search}>
                <SearchIcon />
              </IconButton>
            </Paper>

            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>{localeMessages['filter_by_course'] || 'Course'}</InputLabel>
              <Select
                value={courseFilter}
                label={localeMessages['filter_by_course'] || 'Course'}
                onChange={handleCourseFilterChange}
              >
                <MenuItem value="">{localeMessages['all_courses'] || 'All Courses'}</MenuItem>
                {courses.map(c => (
                  <MenuItem key={c.id} value={String(c.id)}>{c.title}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>{localeMessages['filter_by_status'] || 'Status'}</InputLabel>
              <Select
                value={statusFilter}
                label={localeMessages['filter_by_status'] || 'Status'}
                onChange={handleStatusFilterChange}
              >
                <MenuItem value="">{localeMessages['all_statuses'] || 'All Statuses'}</MenuItem>
                {ENROLLMENT_STATUSES.map(s => (
                  <MenuItem key={s} value={s}>{localeMessages[s] || s}</MenuItem>
                ))}
              </Select>
            </FormControl>

            {isFiltered && (
              <Tooltip title={localeMessages['reset_filters'] || 'Reset Filters'}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<FilterListOffIcon />}
                  onClick={resetFilters}
                >
                  {localeMessages['reset_filters'] || 'Reset'}
                </Button>
              </Tooltip>
            )}
          </Box>

          <TableContainer component={Paper} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{textAlign: direction=="rtl" ? "right" : "left"}}>{localeMessages["learners_list"]}</TableCell>
                  <TableCell sx={{textAlign: direction=="rtl" ? "right" : "left"}}>
                    {courseFilter ? localeMessages['progress'] || 'Progress' : 'Courses'}
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {learners.length === 0 && (
                  <EmptyTableState
                    colSpan={2}
                    message={localeMessages['no_learners_found'] || 'No learners found.'}
                  />
                )}
                {learners.map((learner) => (
                  <TableRow
                    key={learner.id}
                    sx={(theme) => ({
                      ':hover': {
                        backgroundColor: theme.palette.background.dark,
                        cursor: 'pointer',
                      },
                    })}
                    onClick={() => showLearnerEnrollments(learner)}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
                        <Avatar
                          src={learner.photo || undefined}
                          sx={(theme) => ({
                            width: 30,
                            height: 30,
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: '#fff',
                            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.deepPurple[400]} 100%)`,
                          })}
                        >
                          {(learner.email?.[0] || '?').toUpperCase()}
                        </Avatar>
                        <Typography component="span">{learner.email}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}>
                      {courseFilter && learner.enrollmentProgress !== null ? (
                        <Box sx={{ minWidth: 120 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="body2" color="text.secondary">
                              {localeMessages[learner.enrollmentStatus] || learner.enrollmentStatus}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {learner.enrollmentProgress}%
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={learner.enrollmentProgress}
                            sx={{ borderRadius: 1, height: 6 }}
                          />
                        </Box>
                      ) : (
                        <>
                          <Typography variant="body2">{learner.enrollmentsCount.total} enrolled</Typography>
                          <Typography variant="body2" color="text.secondary">{learner.enrollmentsCount.completed} completed</Typography>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          { showPagination && <Pagination sx={{ mt: 2 }} count={pagesCount} onChange={(event, page) => setCurrentPage(page)} /> }
        </Box>
      </Grid>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="md">
        {dialogContent}
      </Dialog>
    </Base>
  )
}

render({children: <Learners />});
