import { Alert, Box, Button } from '@mui/material';
import render from '../../src/render.jsx';
import Layout from '../../public/components/Layout.jsx';


const CommandResult = () => {
    return <Layout>
    { !error_message && !confirmation_message ?<Alert severity='success' sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light" }}>
       {success_message}
    </Alert> : confirmation_message ? <Alert severity="warning" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {confirmation_message}<Box mt={2}><Button href={confirm_url} variant='contained' mt={2}>{localeMessages["Confirm"]}</Button></Box>
    </Alert> : <Alert severity="error" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {error_message} (ref: {ref})
    </Alert>}
    </Layout>
}

render({children: <CommandResult />});
