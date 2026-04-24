import { TextField } from '@mui/material';
import React from 'react';
import { useAppContext } from '../render.jsx';

const RequiredTextField = React.forwardRef(({ label, value, onChange, error, helperText, sx: passedSx = {}, inputProps, slotProps: passedSlotProps = {}, ...props }, ref) => {
    const { direction } = useAppContext();

    const helperTextSlotProps = passedSlotProps.formHelperText ?? {};
    const mergedSlotProps = {
        ...passedSlotProps,
        formHelperText: {
            ...helperTextSlotProps,
            sx: {
                color: 'errorText.main',
                marginLeft: 0,
                ...(helperTextSlotProps.sx ?? {}),
            },
        },
        ...(inputProps || passedSlotProps.htmlInput
            ? {
                htmlInput: {
                    ...(inputProps ?? {}),
                    ...(passedSlotProps.htmlInput ?? {}),
                },
            }
            : {}),
    };

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
            slotProps={mergedSlotProps}
            {...props}
            dir={direction}
        />
    );
});

export default RequiredTextField;
