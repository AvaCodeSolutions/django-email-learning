import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import InboxIcon from '@mui/icons-material/Inbox';

/**
 * A consistent empty-state row to display inside a <TableBody> when there
 * is no data.
 *
 * @param {number}  colSpan  - Number of columns the cell should span.
 * @param {string}  message  - Primary message (e.g. "No courses found.").
 * @param {node}    action   - Optional CTA element (e.g. a <Button>).
 */
function EmptyTableState({ colSpan, message, action }) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan} sx={{ border: 0 }}>
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            py: 6,
            gap: 1,
            color: 'text.disabled',
          }}
        >
          <InboxIcon sx={{ fontSize: 48, opacity: 0.4 }} />
          <Typography variant="body2" color="text.secondary">
            {message}
          </Typography>
          {action && <Box sx={{ mt: 1 }}>{action}</Box>}
        </Box>
      </TableCell>
    </TableRow>
  );
}

export default EmptyTableState;
