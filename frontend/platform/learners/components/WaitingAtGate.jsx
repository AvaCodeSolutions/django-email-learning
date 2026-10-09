import { Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Typography } from '@mui/material';
import LockClockIcon from '@mui/icons-material/LockClock';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import { useState } from 'react';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';

/**
 * Shows that an enrollment is held at a gate, with an admin-only action to unlock it -
 * the same as an unlock call through the API, for when the outside system can't make it.
 *
 * `onUnlocked` is called after a successful unlock so the caller can reload the
 * enrollment; it is also called on a 409, which means the enrollment ended while the
 * dialog was open and the view is out of date.
 */
function WaitingAtGate({ gate, unlockUrl, canUnlock, onUnlocked }) {
  const { localeMessages } = useAppContext();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [unlocking, setUnlocking] = useState(false);
  const [error, setError] = useState(null);

  if (!gate) {
    return null;
  }

  const unlock = () => {
    setUnlocking(true);
    setError(null);
    apiClient.post(unlockUrl, {})
      .then(() => {
        setConfirmOpen(false);
        setUnlocking(false);
        if (onUnlocked) onUnlocked();
      })
      .catch((apiError) => {
        console.error('Error unlocking gate:', apiError);
        setUnlocking(false);
        if (apiError.status === 409) {
          setConfirmOpen(false);
          if (onUnlocked) onUnlocked();
          return;
        }
        setError(localeMessages['gate_unlock_failed'] || 'The gate could not be unlocked.');
      });
  };

  const label = (localeMessages['waiting_at_gate'] || 'Waiting at gate: %(gate)s').replace('%(gate)s', gate.title);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.75, flexWrap: 'wrap' }}>
      <Chip size="small" color="warning" variant="outlined" icon={<LockClockIcon />} label={label} />
      {canUnlock && (
        <Button
          size="small"
          startIcon={<LockOpenIcon />}
          onClick={() => setConfirmOpen(true)}
          sx={{ textTransform: 'none', py: 0 }}
        >
          {localeMessages['unlock_gate'] || 'Unlock'}
        </Button>
      )}

      <Dialog open={confirmOpen} onClose={() => (unlocking ? null : setConfirmOpen(false))} maxWidth="xs" fullWidth>
        <DialogTitle>{localeMessages['unlock_gate_title'] || 'Unlock this gate?'}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {(localeMessages['unlock_gate_confirmation']
              || 'The learner moves past %(gate)s and on to the rest of the course, as if it had been unlocked through the API.'
            ).replace('%(gate)s', gate.title)}
          </DialogContentText>
          {error && (
            <Typography variant="body2" color="error" sx={{ mt: 2 }}>{error}</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} disabled={unlocking} sx={{ textTransform: 'none' }}>
            {localeMessages['cancel'] || 'Cancel'}
          </Button>
          <Button
            onClick={unlock}
            variant="contained"
            disabled={unlocking}
            startIcon={unlocking ? <CircularProgress size={14} color="inherit" /> : null}
            sx={{ textTransform: 'none' }}
          >
            {unlocking
              ? (localeMessages['unlocking'] || 'Unlocking...')
              : (localeMessages['confirm_unlock_gate'] || 'Unlock')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default WaitingAtGate;
