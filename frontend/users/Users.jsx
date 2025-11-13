import Base from '../src/components/Base.jsx'
import { Box, Grid } from '@mui/material'
import render from '../src/render.jsx';


function Users() {

  return (
    <Base
      breadCrumbList={[{label: 'User Management', href: '#'}]}
    >
      <Grid size={{xs: 12}} py={2} pl={2}>
        <Box p={2} sx={{ border: '1px solid', borderColor: 'grey.300', borderRadius: 1, minHeight: 300 }}>
          User Management Page
        </Box>
      </Grid>
    </Base>
  )
}

render({children: <Users />});
