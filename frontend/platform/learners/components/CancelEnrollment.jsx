import { Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Typography } from '@mui/material';
import PersonRemoveIcon from '@mui/icons-material/PersonRemove';
import { useState } from 'react';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';

const CANCELLABLE_STATUSES = ['unverified', 'active'];

/**
 * Admin-only action that ends a learner's enrollment: the enrollment is
 * deactivated as "revoked" and any content still scheduled for the learner is
 * canceled, so nothing further arrives in their inbox.
 *
 * The action cannot be undone — the enrollment state machine has no way out of
 * deactivated — so it asks for confirmation first. `onCanceled` is called after
 * a successful cancellation so the caller can reload the enrollment; it is also
 * called on a 409, which means the enrollment reached a final state through
 * some other route while the dialog was open and the view is out of date.
 */
function CancelEnrollment({ status, cancelUrl, canCancel, onCanceled }) {
  const { localeMessages } = useAppContext();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [canceling, setCanceling] = useState(false);
  const [error, setError] = useState(null);

  if (!canCancel || !CANCELLABLE_STATUSES.includes(status)) {
    return null;
  }

  const cancelEnrollment = () => {
    setCanceling(true);
    setError(null);
    apiClient.post(cancelUrl, {})
      .then(() => {
        setConfirmOpen(false);
        setCanceling(false);
        if (onCanceled) onCanceled();
      })
      .catch((apiError) => {
        console.error('Error canceling enrollment:', apiError);
        setCanceling(false);
        if (apiError.status === 409) {
          setConfirmOpen(false);
          if (onCanceled) onCanceled();
          return;
        }
        setError(localeMessages['enrollment_cancel_failed'] || 'The enrollment could not be canceled.');
      });
  };

  return (
    <Box sx={{ flexShrink: 0 }}>
      <Button
        size="small"
        color="error"
        variant="outlined"
        startIcon={<PersonRemoveIcon />}
        onClick={() => setConfirmOpen(true)}
        sx={{ textTransform: 'none' }}
      >
        {localeMessages['cancel_enrollment'] || 'Cancel enrollment'}
      </Button>

      <Dialog open={confirmOpen} onClose={() => (canceling ? null : setConfirmOpen(false))} maxWidth="xs" fullWidth>
        <DialogTitle>{localeMessages['cancel_enrollment_title'] || 'Cancel this enrollment?'}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {localeMessages['cancel_enrollment_confirmation']
              || 'The learner stops receiving this course immediately and any content still scheduled for them is canceled. This cannot be undone.'}
          </DialogContentText>
          {error && (
            <Typography variant="body2" color="error" sx={{ mt: 2 }}>{error}</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} disabled={canceling} sx={{ textTransform: 'none' }}>
            {localeMessages['keep_enrollment'] || 'Keep enrollment'}
          </Button>
          <Button
            onClick={cancelEnrollment}
            color="error"
            variant="contained"
            disabled={canceling}
            startIcon={canceling ? <CircularProgress size={14} color="inherit" /> : null}
            sx={{ textTransform: 'none' }}
          >
            {canceling
              ? (localeMessages['canceling'] || 'Canceling...')
              : (localeMessages['confirm_cancel_enrollment'] || 'Cancel enrollment')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default CancelEnrollment;
