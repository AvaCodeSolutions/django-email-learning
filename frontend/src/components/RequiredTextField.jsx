import { TextField } from '@mui/material';
import React from 'react';

const RequiredTextField = React.forwardRef(({ label, value, onChange, error, helperText, sx: passedSx = {}, ...props }, ref) => {
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
            sx={{...passedSx, label: { right: direction === 'rtl' ? "25px" : 'auto', left: direction === 'rtl' ? 'auto' : 0, '&.MuiInputLabel-shrink': {right: direction === 'rtl' ? '30px' : 'auto', transformOrigin: direction === 'rtl' ? 'top right' : 'top left', left: direction === 'rtl' ? 'auto' : 0} }}}
            slotProps={{ formHelperText: { sx: { color: 'errorText.main', marginLeft: 0 } } }}
            {...props}
            dir={direction}
        />
    );
});

export default RequiredTextField;
