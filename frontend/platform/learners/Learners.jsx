import Base from '../../src/components/Base.jsx'
import { InputBase, IconButton, Accordion, AccordionDetails, AccordionSummary, Box, Dialog, Grid, LinearProgress, Pagination, Paper, TableContainer, Table, TableBody, TableHead, TableCell, TableRow, Typography } from '@mui/material'
import { Timeline, TimelineItem, TimelineContent, TimelineOppositeContent, TimelineSeparator, TimelineConnector, TimelineDot } from '@mui/lab'
import { useState, useEffect, useRef } from 'react'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AppRegistrationIcon from '@mui/icons-material/AppRegistration';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import LibraryBooksIcon from '@mui/icons-material/LibraryBooks';
import BallotIcon from '@mui/icons-material/Ballot';
import AssignmentReturnedIcon from '@mui/icons-material/AssignmentReturned';
import SearchIcon from '@mui/icons-material/Search';
import SchoolIcon from '@mui/icons-material/School';
import BackspaceIcon from '@mui/icons-material/Backspace';
import render from '../../src/render.jsx';
import { getCookie } from '../../src/utils.js';
import { lazy, Suspense } from "react";

const EnrollentList = lazy(() => import("./components/EnrollmentList.jsx"));


const apiBaseUrl = localStorage.getItem('apiBaseUrl');


function Learners(initialQs="") {

  const [organizationId, setOrganizationId] = useState(null);
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
        <Box p={2}>
          <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>{localeMessages["enrollment_details"]}</Typography>
          <Typography>{data.learner.email}</Typography>
          <Typography variant="subtitle1">{data.course.title}</Typography>
          <Typography>{localeMessages["enrollment_id"]}: {data.id}</Typography>
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
                  <Box><Typography>{localeMessages["result"]}: {event.event_data.is_passed ? localeMessages["passed"] : localeMessages["failed"]}</Typography></Box>
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
          {/* Add more details as needed */}
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
    if (learner.state !== 0) {
      return;
    }
    learner.state = 1; // loading
    setLearners([...learners]);

    const apiBaseUrl = localStorage.getItem('apiBaseUrl');
    fetch(`${apiBaseUrl}/organizations/${organizationId}/learners/${learner.id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
    .then(response => response.json())
    .then(data => {
      learner.enrollments = data.enrollments;
      learner.state = 2; // loaded
      setLearners([...learners]);
    })
    .catch(error => {
      console.error('Error fetching enrollments for learner:', error);
      learner.state = 0; // reset to not loaded on error
      setLearners([...learners]);
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
      <Grid size={{xs: 12, lg: 8}} py={2} pl={2}>
        <Box p={2} sx={(theme) => ({ marginBottom: 2, border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300, backgroundColor: theme.palette.background.nav })}>

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

          <TableContainer component={Paper} sx={{ maxHeight: 440, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{textAlign: direction=="rtl" ? "right" : "left"}}>{localeMessages["learners_list"]}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {learners.map((learner) => (
                  <TableRow key={learner.id}>
                    <TableCell>
                      <Accordion onChange={() => {loadEnrollments(learner)}}>
                        <AccordionSummary
                          expandIcon={<ExpandMoreIcon />}
                          aria-controls="panel1-content"
                          id="panel1-header"
                        >
                          <Typography component="span">{learner.email}</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography component="span">{learner.state === 0 ? "" : learner.state === 1 ? <LinearProgress /> : <Suspense fallback={<Box sx={{ p: 2 }}><LinearProgress /></Box>}><EnrollentList enrollments={learner.enrollments} selectHandler={showEnrollmentStatus}/></Suspense>}</Typography>
                        </AccordionDetails>
                      </Accordion>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          { showPagination && <Pagination sx={{ mt: 2 }} count={pagesCount} onChange={(event, page) => setCurrentPage(page)} /> }
        </Box>
      </Grid>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        {dialogContent}
      </Dialog>
    </Base>
  )
}

render({children: <Learners />});
