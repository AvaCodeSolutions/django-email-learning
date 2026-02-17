import { Box, Typography, RadioGroup, FormControlLabel, Radio } from '@mui/material';
import { useAppContext } from '../../../src/render.jsx';

const FilterForm = ({ onStatusChange }) => {
  const { localeMessages } = useAppContext();
  return (
    <>
      <Typography variant="body2" component="div" sx={{ mb: 2, fontWeight: 'bold' }}>
        {localeMessages["filter"]}
      </Typography>
      <Typography variant="subtitle2" component="div" sx={{ mb: 1, fontWeight: 'bold' }}>
        {localeMessages["course_status"]}:
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
        <FormControlLabel value="all" control={<Radio />} label={localeMessages["all"]} />
        <FormControlLabel value="enabled" control={<Radio />} label={localeMessages["enabled"]} />
        <FormControlLabel value="disabled" control={<Radio />} label={localeMessages["disabled"]} />
      </RadioGroup>
    </>
  );
};
export default FilterForm;
