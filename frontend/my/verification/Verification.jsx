import { Alert, Box } from '@mui/material';
import render from '../../src/render.jsx';


const Verification = () => {
    return <>
    { !error_message ?<Alert severity='success' textAlign="left" sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light" }}>
        You have successfully verified your enrollment.
    </Alert> : <Alert severity="error" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {error_message} (ref: {ref})
    </Alert>}
    </>
}

render({children: <Verification />});
