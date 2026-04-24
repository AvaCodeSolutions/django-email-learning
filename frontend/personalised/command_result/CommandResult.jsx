import { Alert, Box, Button, Typography } from '@mui/material';
import render, { useAppContext } from '../../src/render.jsx';
import Layout from '../../public/components/Layout.jsx';


const CommandResult = () => {
    const { successMessage, confirmationMessage, confirmUrl, errorMessage, ref, localeMessages } = useAppContext();
    return <Layout>
    { !errorMessage && !confirmationMessage ?<Alert severity='success' sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light" }}>
       {successMessage}
    </Alert> : confirmationMessage ? <Box sx={{ my: 6 }}><Typography variant='h6' align='center' sx={{ mt: 4, color: 'text.primary' }}>
       {confirmationMessage}
    </Typography> <Box sx={{ mt: 6, textAlign: 'center' }}><Button href={confirmUrl} variant='contained' sx={{ mt: 2, mx: 'auto', px: 3, fontSize: '1rem' }}>{localeMessages["Confirm"]}</Button></Box></Box>: <Alert severity="error" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {errorMessage} (ref: {ref})
    </Alert>}
    </Layout>
}

render({children: <CommandResult />});
