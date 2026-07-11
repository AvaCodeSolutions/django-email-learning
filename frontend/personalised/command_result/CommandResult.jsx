import { Alert, Box, Button, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import render, { useAppContext } from '../../src/render.jsx';
import Layout from '../../public/components/Layout.jsx';
import logoVerticalLightUrl from '../../src/assets/logo-v-light.png';
import logoVerticalDarkUrl from '../../src/assets/logo-v-dark.png';


const CommandResult = () => {
    const { successMessage, confirmationMessage, confirmUrl, errorMessage, ref, localeMessages, customLogo } = useAppContext();
    const theme = useTheme();

    let logoUrl;
    if (customLogo) {
        logoUrl = theme.palette.mode === 'light' ? (customLogo.verticalLight ? customLogo.verticalLight : customLogo.verticalDark) : (customLogo.verticalDark ? customLogo.verticalDark : customLogo.verticalLight);
    }
    if (!logoUrl) {
        logoUrl = theme.palette.mode === 'light' ? logoVerticalLightUrl : logoVerticalDarkUrl;
    }

    const showCloseWindowMessage = !confirmationMessage && localeMessages?.close_window_message;

    return <Layout fullHeight>
    <Box sx={{ textAlign: 'center', py: { xs: 3, md: 4 } }}>
        <Box component="img" src={logoUrl} alt="Logo" sx={{ width: { xs: 160, md: 200 }, maxWidth: '80%', mb: { xs: 4, md: 6 } }} />
        { !errorMessage && !confirmationMessage ? <Alert severity='success' sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light" }}>
           {successMessage}
        </Alert> : confirmationMessage ? <Box><Typography variant='h6' align='center' sx={{ color: 'text.primary' }}>
           {confirmationMessage}
        </Typography> <Box sx={{ mt: 4 }}><Button href={confirmUrl} variant='contained' sx={{ px: 3, fontSize: '1rem' }}>{localeMessages["Confirm"]}</Button></Box></Box>: <Alert severity="error" sx={{ maxWidth: 800, margin: '0 auto' }}>
           {errorMessage} (ref: {ref})
        </Alert>}
        { showCloseWindowMessage && <Typography variant='body2' align='center' sx={{ mt: 3, color: 'text.secondary' }}>
            {localeMessages.close_window_message}
        </Typography> }
    </Box>
    </Layout>
}

render({children: <CommandResult />});
