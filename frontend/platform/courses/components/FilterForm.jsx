import { Box, Typography, RadioGroup, FormControlLabel, Radio } from '@mui/material';

const FilterForm = ({ onStatusChange }) => {
  return (
    <>
      <Typography variant="body2" component="div" sx={{ mb: 2, fontWeight: 'bold' }}>
        Filter
      </Typography>
      <Typography variant="subtitle2" component="div" sx={{ mb: 1, fontWeight: 'bold' }}>
        Course Status:
      </Typography>
      <RadioGroup defaultValue="all" name="course-status-radio-group" onChange={(event) => {
        const value = event.target.value;
        if (value === 'all') {
          onStatusChange("");
        } else if (value === 'enabled') {
          onStatusChange("?enabled=true");
        } else if (value === 'disabled') {
          onStatusChange("?enabled=false");
        }
      }}>
        <FormControlLabel value="all" control={<Radio />} label="All" />
        <FormControlLabel value="enabled" control={<Radio />} label="Enabled" />
        <FormControlLabel value="disabled" control={<Radio />} label="Disabled" />
      </RadioGroup>
    </>
  );
};
export default FilterForm;
