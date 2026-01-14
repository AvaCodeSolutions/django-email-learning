import GlobalStyles from '@mui/material/GlobalStyles';
import Container from '@mui/material/Container';


const Layout = ({ children }) => {
    return (<>
        <GlobalStyles styles={(theme) => ({ body: { margin: 0, padding: 0, backgroundColor: theme.palette.background.dark, color: theme.palette.text.primary } })} />
        <Container sx={{ backgroundColor: 'background.paper', padding: 4, marginTop: 4, borderRadius: 2 }}>
        {children}
        </Container>
    </>);
}

export default Layout;
