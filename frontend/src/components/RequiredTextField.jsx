import { TextField } from '@mui/material';

function RequiredTextField({ label, value, onChange, error, helperText, ...props }) {
    return (
        <TextField
            label={label}
            value={value}
            onChange={onChange}
            error={error}
            helperText={helperText}
            required
            slotProps={{ formHelperText: { sx: { color: 'primary.dark' } } }}
            {...props}
        />
    );
}

export default RequiredTextField;
