import { Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Typography } from '@mui/material';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import { useState } from 'react';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';

/**
 * An admin-only action to confirm an unverified enrollment. In a `gated` course it shows that
 * the enrollment is waiting at the enrollment gate, and confirming is the same as unlocking
 * that gate through the API, for when the outside system can't. In a course confirmed by
 * email link it verifies the enrollment for a learner who can't use their link.
 *
 * `onConfirmed` is called after a successful confirmation so the caller can reload the
 * enrollment; it is also called on a 409, which means the enrollment ended while the
 * dialog was open and the view is out of date.
 */
function WaitingForConfirmation({ confirmUrl, canConfirm, onConfirmed, gated = true }) {
  const { localeMessages } = useAppContext();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState(null);

  if (!gated && !canConfirm) {
    return null;
  }

  const actionLabel = gated
    ? (localeMessages['confirm_enrollment'] || 'Confirm enrollment')
    : (localeMessages['verify_enrollment'] || 'Verify enrollment');

  const confirm = () => {
    setConfirming(true);
    setError(null);
    apiClient.post(confirmUrl, {})
      .then(() => {
        setConfirmOpen(false);
        setConfirming(false);
        if (onConfirmed) onConfirmed();
      })
      .catch((apiError) => {
        console.error('Error confirming enrollment:', apiError);
        setConfirming(false);
        if (apiError.status === 409) {
          setConfirmOpen(false);
          if (onConfirmed) onConfirmed();
          return;
        }
        setError(localeMessages['enrollment_confirm_failed'] || 'The enrollment could not be confirmed.');
      });
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.75, flexWrap: 'wrap' }}>
      {gated && (
        <Chip
          size="small"
          color="warning"
          variant="outlined"
          icon={<HourglassEmptyIcon />}
          label={localeMessages['waiting_for_confirmation'] || 'Waiting at the enrollment gate'}
        />
      )}
      {canConfirm && (
        <Button
          size="small"
          startIcon={<HowToRegIcon />}
          onClick={() => setConfirmOpen(true)}
          sx={{ textTransform: 'none', py: 0 }}
        >
          {actionLabel}
        </Button>
      )}

      <Dialog open={confirmOpen} onClose={() => (confirming ? null : setConfirmOpen(false))} maxWidth="xs" fullWidth>
        <DialogTitle>
          {gated
            ? (localeMessages['confirm_enrollment_title'] || 'Confirm this enrollment?')
            : (localeMessages['verify_enrollment_title'] || 'Verify this enrollment?')}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {gated
              ? (localeMessages['confirm_enrollment_confirmation']
                || 'The enrollment becomes active, the learner is sent the welcome email and their first content is scheduled, as if the enrollment gate had been unlocked through the API.')
              : (localeMessages['verify_enrollment_confirmation']
                || "The enrollment becomes active without the learner following their verification link. They are sent the welcome email and their first content is scheduled. Only do this if you know the email address is theirs.")}
          </DialogContentText>
          {error && (
            <Typography variant="body2" color="error" sx={{ mt: 2 }}>{error}</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} disabled={confirming} sx={{ textTransform: 'none' }}>
            {localeMessages['cancel'] || 'Cancel'}
          </Button>
          <Button
            onClick={confirm}
            variant="contained"
            disabled={confirming}
            startIcon={confirming ? <CircularProgress size={14} color="inherit" /> : null}
            sx={{ textTransform: 'none' }}
          >
            {confirming ? (localeMessages['confirming'] || 'Confirming...') : actionLabel}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default WaitingForConfirmation;
