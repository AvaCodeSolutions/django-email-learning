import GlobalStyles from '@mui/material/GlobalStyles';
import Container from '@mui/material/Container';
import { Box, Typography, Link } from '@mui/material';


const Layout = ({ children }) => {
    return (<>
        <GlobalStyles styles={(theme) => ({ body: { margin: 0, padding: 0, backgroundColor: theme.palette.background.dark, color: theme.palette.text.primary } })} />
        <Container sx={{ backgroundColor: 'background.paper', padding: 4, marginTop: { xs: 0, md: "32px" }, borderRadius: 2, boxShadow: 2 }}>
        {children}
        </Container>

        {/* Footer Credit for Public Pages */}
        <Box
          component="footer"
          sx={{
            position: 'fixed',
            bottom: 0,
            right: 16,
            padding: 1,
            zIndex: 1000,
            backgroundColor: 'transparent'
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: 'text.secondary',
              fontSize: '0.7rem',
              opacity: 0.8
            }}
          >
            Powered by{' '}
            <Link
              href="https://github.com/AvaCodeSolutions/django-email-learning"
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                color: 'primary.main',
                textDecoration: 'none',
                '&:hover': {
                  textDecoration: 'underline'
                }
              }}
            >
              Django Email Learning
            </Link>
          </Typography>
        </Box>
    </>);
}

export default Layout;
