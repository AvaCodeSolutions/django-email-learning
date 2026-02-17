import { Alert, Box, Button } from '@mui/material';
import render, { useAppContext } from '../../src/render.jsx';
import Layout from '../../public/components/Layout.jsx';


const CommandResult = () => {
    const { successMessage, confirmationMessage, confirmUrl, errorMessage, ref, localeMessages } = useAppContext();
    return <Layout>
    { !errorMessage && !confirmationMessage ?<Alert severity='success' sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light" }}>
       {successMessage}
    </Alert> : confirmationMessage ? <Alert severity="warning" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {confirmationMessage}<Box mt={2}><Button href={confirmUrl} variant='contained' mt={2}>{localeMessages["Confirm"]}</Button></Box>
    </Alert> : <Alert severity="error" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {errorMessage} (ref: {ref})
    </Alert>}
    </Layout>
}

render({children: <CommandResult />});
