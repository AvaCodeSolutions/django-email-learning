import { Alert, Box } from '@mui/material';
import render from '../../src/render.jsx';
import Layout from '../../public/components/Layout.jsx';


const CommandResult = () => {
    return <Layout>
    { !error_message ?<Alert severity='success' sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light" }}>
       {success_message}
    </Alert> : <Alert severity="error" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {error_message} (ref: {ref})
    </Alert>}
    </Layout>
}

render({children: <CommandResult />});
