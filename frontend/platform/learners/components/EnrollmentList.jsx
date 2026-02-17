import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography } from '@mui/material';
import { useAppContext } from '../../../src/render.jsx';

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
          </TableRow>
        </TableHead>
        <TableBody>
          {enrollments.map((enrollment) => (
            <TableRow
            key={enrollment.id} sx={(theme) => ({':hover': {backgroundColor: theme.palette.background.dark, cursor: 'pointer', borderBottomColor: 'secondary.light', borderBottomWidth: 2, borderBottomStyle: 'solid'}})}
            onClick={() => selectHandler(enrollment.id)}>
              <TableCell align={direction=="rtl" ? "right" : "left"}>{enrollment.course_title}</TableCell>
              <TableCell align={direction=="rtl" ? "right" : "left"}>{localeMessages[enrollment.status]}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default EnrollentList;
