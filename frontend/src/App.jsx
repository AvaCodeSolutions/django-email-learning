import { Grid, Box } from '@mui/material'
import Base from './components/Base'


function App() {

  return (
    <Base breadCrumbList={[]}>
      <Grid size={{xs: 12, md: 9}} py={2} pl={2}>
          <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300 }}>
            Empty Page
          </Box>
      </Grid>
    </Base>
  )
}

export default App
