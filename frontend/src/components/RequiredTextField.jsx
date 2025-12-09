import { TextField } from '@mui/material';
import React from 'react';

const RequiredTextField = React.forwardRef(({ label, value, onChange, error, helperText, ...props }, ref) => {
    console.log('RequiredTextField rendered, ref:', ref);
    return (
        <TextField
            ref={ref}
            label={label}
            value={value}
            onChange={onChange}
            error={error}
            helperText={helperText}
            required
            slotProps={{ formHelperText: { sx: { color: 'errorText.main', marginLeft: 0 } } }}
            {...props}
        />
    );
});

export default RequiredTextField;
