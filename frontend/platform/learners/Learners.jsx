import Base from '../../src/components/Base.jsx'
import { Avatar, InputBase, IconButton, Box, Chip, Dialog, Grid, LinearProgress, Pagination, Paper, TableContainer, Table, TableBody, TableHead, TableCell, TableRow, Typography } from '@mui/material'
import { Timeline, TimelineItem, TimelineContent, TimelineOppositeContent, TimelineSeparator, TimelineConnector, TimelineDot } from '@mui/lab'
import { useState, useEffect, useRef } from 'react'
import AppRegistrationIcon from '@mui/icons-material/AppRegistration';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import LibraryBooksIcon from '@mui/icons-material/LibraryBooks';
import BallotIcon from '@mui/icons-material/Ballot';
import AssignmentReturnedIcon from '@mui/icons-material/AssignmentReturned';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import SearchIcon from '@mui/icons-material/Search';
import SchoolIcon from '@mui/icons-material/School';
import BackspaceIcon from '@mui/icons-material/Backspace';
import render, { useAppContext } from '../../src/render.jsx';
import { getCookie } from '../../src/utils.js';
import { lazy, Suspense } from "react";

const EnrollentList = lazy(() => import("./components/EnrollmentList.jsx"));


function Learners(initialQs="") {

  const [organizationId, setOrganizationId] = useState(null);
  const { localeMessages, direction, apiBaseUrl } = useAppContext();
  const [learners, setLearners] = useState([]);
  const searcchInputRef = useRef(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogContent, setDialogContent] = useState(null);
  const [qs, setQs] = useState(initialQs);
  const [showPagination, setShowPagination] = useState(false);
  const pageSize = 20;
  const [pagesCount, setPagesCount] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);

  const eventMap = {
    'registered': {icon: <AppRegistrationIcon sx={{ color: 'white' }} />, color: "#00bcd4", title: localeMessages["learner_registered"]},
    'verified': {icon: <HowToRegIcon />, color: "#66bb6a", title: localeMessages["learner_verified"]},
    'content_sent_lesson': {icon: <LibraryBooksIcon />, color: "#00acc1", title: localeMessages["lesson_sent"]},
    'content_sent_quiz': {icon: <BallotIcon />, color: "#26a69a", title: localeMessages["quiz_sent"]},
    'quiz_submitted': {icon: <AssignmentReturnedIcon />, color: "#26a69a", title: localeMessages["quiz_submitted"]},
    'course_completed': {icon: <SchoolIcon />, color: "#0097a7", title: localeMessages["course_completed"]},
    'deactivated': {icon: <BackspaceIcon />, color: "#b71c1c", title: localeMessages["learner_deactivated"]},
  };


  const showEnrollmentStatus = (enrollmentId) => {
    setDialogOpen(true);
    setDialogContent(<LinearProgress sx={{ m: 10 }} />);
    fetch(`${apiBaseUrl}/organizations/${organizationId}/enrollments/${enrollmentId}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
    .then(response => response.json())
    .then(data => {
      setDialogContent(
        <Box>
          <Box sx={{ px: 3, pt: 3, pb: 2, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={(theme) => ({ width: 44, height: 44, fontSize: '1.1rem', fontWeight: 700, color: '#fff', background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.deepPurple?.[400] ?? theme.palette.secondary.main} 100%)` })}>
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
                { event.type === "content_sent" && <>
                  <Box><Typography>{event.event_data.course_content_title}</Typography></Box>
                </>}
                { event.type === "deactivated" && <>
                  <Box><Typography>{localeMessages["reason"]}: {event.event_data.reason}</Typography></Box>
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

    fetch(`${apiBaseUrl}/organizations/${organizationId}/learners/?${qs}&page_size=${pageSize}&page=${currentPage}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
    .then(response => response.json())
    .then(data => {
      setShowPagination(data.page != 1 || data.has_more);
      setPagesCount(Math.ceil(data.total_count / pageSize));
      setLearners(data.items.map(learner => ({
        id: learner.id,
        email: learner.email,
        enrollmentsCount: learner.enrollments_count || { total: 0, completed: 0 },
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

  const loadEnrollments = (learner) => {
    if (learner.state === 2) {
      return Promise.resolve(learner.enrollments);
    }

    setLearners((prevLearners) => prevLearners.map((item) => (
      item.id === learner.id ? { ...item, state: 1 } : item
    )));

    return fetch(`${apiBaseUrl}/organizations/${organizationId}/learners/${learner.id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
    .then(response => response.json())
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
            <Avatar sx={(theme) => ({ width: 44, height: 44, fontSize: '1.1rem', fontWeight: 700, color: '#fff', background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.deepPurple?.[400] ?? theme.palette.secondary.main} 100%)` })}>
              {(learner.email?.[0] || '?').toUpperCase()}
            </Avatar>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{learner.email}</Typography>
          </Box>
          <Box sx={{ p: 2 }}>
          <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}>
            <EnrollentList enrollments={enrollments} selectHandler={showEnrollmentStatus} />
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
    setQs(`search=${encodeURIComponent(searcchInputRef.current.value)}`);
  }

  return (
    <Base
          breadCrumbList={[{label: localeMessages["learners"], href: '#'}]}
          organizationIdRefreshCallback={setOrganizationId}
        >
      <Grid size={{xs: 12}} sx={{ py: 2, pl: 2 }}>
        <Box sx={{ p: 2, marginBottom: 2, border: '1px solid', borderColor: 'border.main', borderRadius: 2, minHeight: 300, backgroundColor: 'background.box' }}>

          <Paper
            sx={{ mb: '10px', p: '2px 4px', display: 'flex', alignItems: 'center', width: 400 }}
          >
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

          <TableContainer component={Paper} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{textAlign: direction=="rtl" ? "right" : "left"}}>{localeMessages["learners_list"]}</TableCell>
                  <TableCell sx={{textAlign: direction=="rtl" ? "right" : "left"}}>Courses</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
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
                      <Typography variant="body2">{learner.enrollmentsCount.total} enrolled</Typography>
                      <Typography variant="body2" color="text.secondary">{learner.enrollmentsCount.completed} completed</Typography>
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
