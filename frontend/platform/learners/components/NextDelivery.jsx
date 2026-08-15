import { Box, CircularProgress, Link, Typography } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { useState } from 'react';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';

/**
 * The enrollment's next scheduled content delivery, with an admin-only
 * "send now" link that delivers it immediately instead of waiting for the
 * delivery job's next run.
 *
 * `onSent` is called after a successful send so the caller can reload the
 * enrollment — the timeline gains a "content sent" event and the next
 * delivery moves on to whatever was scheduled after it.
 */
function NextDelivery({ nextDelivery, sendUrl, canSend, onSent }) {
  const { localeMessages } = useAppContext();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  if (!nextDelivery) {
    return null;
  }

  const scheduledAt = String(nextDelivery.scheduled_at || '').replace('T', ' ').replace('Z', '');

  const sendNow = () => {
    setSending(true);
    setError(null);
    apiClient.post(sendUrl, {})
      .then(() => {
        if (onSent) onSent();
      })
      .catch((apiError) => {
        console.error('Error sending content delivery:', apiError);
        setError(apiError.status === 409
          ? (localeMessages['delivery_no_longer_scheduled'] || 'This delivery is no longer scheduled.')
          : (localeMessages['content_send_failed'] || 'The content could not be sent.'));
        setSending(false);
      });
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
        <Box component="span">
          {localeMessages['next_delivery'] || 'Next delivery'}: {scheduledAt} — {nextDelivery.course_content_title}
        </Box>
        {canSend && (
          <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center' }}>
            (
            {sending ? (
              <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
                <CircularProgress size={12} />
                {localeMessages['sending'] || 'Sending...'}
              </Box>
            ) : (
              <Link
                component="button"
                type="button"
                variant="body2"
                underline="hover"
                onClick={sendNow}
                sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, verticalAlign: 'baseline' }}
              >
                <SendIcon sx={{ fontSize: '0.95rem' }} />
                {localeMessages['send_now'] || 'send now'}
              </Link>
            )}
            )
          </Box>
        )}
      </Typography>
      {error && (
        <Typography variant="body2" color="error">{error}</Typography>
      )}
    </Box>
  );
}

export default NextDelivery;
