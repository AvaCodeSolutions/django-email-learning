import { Box, IconButton, LinearProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Tooltip, Typography } from '@mui/material';
import WorkspacePremiumIcon from '@mui/icons-material/WorkspacePremium';
import { useAppContext } from '../../../src/render.jsx';

function LinearProgressWithLabel({ value, direction }) {
  const normalized = Math.min(100, Math.max(0, value || 0));

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <LinearProgress
        variant="determinate"
        value={normalized}
        sx={(theme) => ({
          flex: 1,
          height: 8,
          borderRadius: 4,
          backgroundColor: theme.palette.mode === 'light' ? theme.palette.grey[100] : theme.palette.grey[800],
          '& .MuiLinearProgress-bar': {
            borderRadius: 4,
          },
        })}
      />
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ minWidth: 38, textAlign: direction === 'rtl' ? 'left' : 'right' }}
      >
        {normalized}%
      </Typography>
    </Box>
  );
}

function EnrollentList({enrollments, selectHandler}) {
  const { localeMessages, direction } = useAppContext();
  if (enrollments.length === 0) {
    return <Typography component="span">{localeMessages["nor_enrollments_found"]}</Typography>
  }

  return (
    <TableContainer component={Paper} sx={{ maxHeight: 300, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell align={direction=="rtl" ? "right" : "left"}>{localeMessages["course"]}</TableCell>
            <TableCell align={direction=="rtl" ? "right" : "left"}>{localeMessages["status"]}</TableCell>
            <TableCell align={direction=="rtl" ? "right" : "left"}>{localeMessages["progress"] || 'Progress'}</TableCell>
            <TableCell align={direction=="rtl" ? "right" : "left"}>{localeMessages["certificate"] || 'Certificate'}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {enrollments.map((enrollment) => (
            <TableRow
            key={enrollment.id} sx={(theme) => ({':hover': {backgroundColor: theme.palette.background.dark, cursor: 'pointer', borderBottomColor: 'primary.light', borderBottomWidth: 2, borderBottomStyle: 'solid'}})}
            onClick={() => selectHandler(enrollment.id)}>
              <TableCell align={direction=="rtl" ? "right" : "left"}>{enrollment.course_title}</TableCell>
              <TableCell align={direction=="rtl" ? "right" : "left"}>{localeMessages[enrollment.status]}</TableCell>
              <TableCell align={direction=="rtl" ? "right" : "left"} sx={{ minWidth: 170 }}>
                <LinearProgressWithLabel value={enrollment.progress} direction={direction} />
              </TableCell>
              <TableCell align={direction=="rtl" ? "right" : "left"}>
                {enrollment.certificate_url ? (
                  <Tooltip title={localeMessages["certificate"] || 'Certificate'}>
                    <IconButton
                      component="a"
                      href={enrollment.certificate_url}
                      rel="noopener noreferrer"
                      size="small"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <WorkspacePremiumIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default EnrollentList;
