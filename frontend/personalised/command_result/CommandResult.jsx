import { Alert, Box, Button, Checkbox, FormControlLabel, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import render, { useAppContext } from '../../src/render.jsx';
import Layout from '../../public/components/Layout.jsx';
import ShareButtons from '../../public/components/ShareButtons.jsx';
import logoVerticalLightUrl from '../../src/assets/logo-v-light.png';
import logoVerticalDarkUrl from '../../src/assets/logo-v-dark.png';
import { sanitizeImageUrl, sanitizeUrl } from '../../src/sanitizeUrl.js';
import { getCookie } from '../../src/utils.js';

const GOLDEN_RATIO = 1.618;
const GOLDEN_RATIO_SQUARED = GOLDEN_RATIO * GOLDEN_RATIO;

const CommandResult = () => {
    const { successMessage, shareUrl: rawShareUrl, shareTitle, confirmationMessage, confirmUrl: rawConfirmUrl, confirmToken, errorMessage, ref, localeMessages, customLogo } = useAppContext();
    const confirmUrl = sanitizeUrl(rawConfirmUrl);
    const shareUrl = sanitizeUrl(rawShareUrl);
    const csrfToken = getCookie('csrftoken');
    const theme = useTheme();

    let logoUrl;
    if (customLogo) {
        // Sanitized before the fallback check so an unusable custom logo
        // falls through to the bundled default rather than a broken image.
        const verticalLight = sanitizeImageUrl(customLogo.verticalLight);
        const verticalDark = sanitizeImageUrl(customLogo.verticalDark);
        logoUrl = theme.palette.mode === 'light' ? (verticalLight ? verticalLight : verticalDark) : (verticalDark ? verticalDark : verticalLight);
    }
    if (!logoUrl) {
        logoUrl = theme.palette.mode === 'light' ? logoVerticalLightUrl : logoVerticalDarkUrl;
    }

    // After a successful enrollment the learner is invited to share the course
    // instead of being told to close the window.
    const showShareButtons = !errorMessage && !confirmationMessage && Boolean(shareUrl);
    const showCloseWindowMessage = !confirmationMessage && !showShareButtons && localeMessages?.close_window_message;

    return <Layout fullHeight>
    <Box sx={{ flexGrow: 1 }} />
    <Box sx={{ textAlign: 'center', py: { xs: 3, md: 4 } }}>
        <Box component="img" src={logoUrl} alt="Logo" sx={{ width: { xs: 160, md: 200 }, maxWidth: '80%', mb: { xs: 4, md: 6 } }} />
        { !errorMessage && !confirmationMessage ? <Alert severity='success' sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light", textAlign: showCloseWindowMessage || showShareButtons ? 'center' : 'left' }}>
           {successMessage}
        </Alert> : confirmationMessage ? <Box><Typography variant='h6' align='center' sx={{ color: 'text.primary' }}>
           {confirmationMessage}
        </Typography>
        {localeMessages?.confirm_required_message && <Alert severity='warning' sx={{ maxWidth: 800, margin: '16px auto 0' }}>
           {localeMessages.confirm_required_message}
        </Alert>}
        <Box component='form' method='post' action={confirmUrl} sx={{ mt: 4 }}>
            <input type='hidden' name='token' value={confirmToken || ''} />
            <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken || ''} />
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                <FormControlLabel
                    control={<Checkbox name='confirm' required />}
                    label={localeMessages['confirm_checkbox_label']}
                    sx={{ m: 0, color: 'text.primary' }}
                />
            </Box>
            <Button type='submit' variant='contained' sx={{ px: 3, fontSize: '1rem' }}>{localeMessages['Unsubscribe']}</Button>
        </Box></Box>: <Alert severity="error" sx={{ maxWidth: 800, margin: '0 auto', textAlign: showCloseWindowMessage ? 'center' : 'left' }}>
           {errorMessage} (ref: {ref})
        </Alert>}
        { showShareButtons && <Box sx={{ mt: 3 }}>
            <ShareButtons
                url={shareUrl}
                title={shareTitle || ''}
                messages={localeMessages || {}}
                label={localeMessages?.share_after_enrollment}
                centered
            />
        </Box> }
        { showCloseWindowMessage && <Typography variant='body2' align='center' sx={{ mt: 3, color: 'text.secondary' }}>
            {localeMessages.close_window_message}
        </Typography> }
    </Box>
    <Box sx={{ flexGrow: GOLDEN_RATIO_SQUARED }} />
    </Layout>
}

export { CommandResult };

render({children: <CommandResult />});
