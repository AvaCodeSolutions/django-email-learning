import GlobalStyles from '@mui/material/GlobalStyles';
import Container from '@mui/material/Container';
import { Box, Typography, Link } from '@mui/material';


const Layout = ({ children }) => {
    return (<>
        <GlobalStyles styles={(theme) => ({ body: { margin: 0, padding: 0, backgroundColor: theme.palette.background.dark, color: theme.palette.text.primary } })} />
        <Container sx={{ backgroundColor: 'background.paper', padding: 4, marginTop: { xs: 0, md: "32px" }, borderRadius: 2, boxShadow: 2 }}>
        {children}
        </Container>
    </>);
}

export default Layout;
