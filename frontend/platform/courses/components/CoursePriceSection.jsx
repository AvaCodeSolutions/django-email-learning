import { Autocomplete, Box, TextField, Typography } from '@mui/material';
import { useMemo } from 'react';
import { PRICE_SUBTITLE_MAX_LENGTH } from './coursePrice.js';

const currencyCodes = () => {
    try {
        return Intl.supportedValuesOf('currency');
    } catch {
        return ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CHF', 'INR', 'CNY', 'SEK', 'NOK', 'DKK', 'BRL', 'MXN'];
    }
};

const currencyName = (displayNames, code) => {
    try {
        return displayNames?.of(code) || code;
    } catch {
        return code;
    }
};

export default function CoursePriceSection({ value, onChange, errors = {}, readOnly = false, direction, localeMessages }) {
    const currencyOptions = useMemo(() => {
        let displayNames = null;
        try {
            displayNames = new Intl.DisplayNames([document.documentElement.lang || 'en'], { type: 'currency' });
        } catch {
            displayNames = null;
        }
        const codes = currencyCodes();
        // Keep a stored code selectable even when this browser doesn't list it.
        if (value.currency && !codes.includes(value.currency)) {
            codes.push(value.currency);
        }
        return codes.map((code) => ({ code, label: `${code} - ${currencyName(displayNames, code)}` }));
    }, [value.currency]);

    const selectedCurrency = currencyOptions.find((option) => option.code === value.currency) || null;
    const update = (field, fieldValue) => onChange({ ...value, [field]: fieldValue });

    return (
        <Box sx={{ mt: 1 }}>
            <Typography variant="subtitle1">{localeMessages['course_price_section']}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {localeMessages['course_price_section_helper_text']}
            </Typography>
            <Box
                sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1fr) minmax(0, 1fr)' },
                    columnGap: 2,
                }}
            >
                <TextField
                    label={localeMessages['course_price']}
                    fullWidth
                    margin="normal"
                    value={value.price}
                    disabled={readOnly}
                    error={Boolean(errors.price)}
                    helperText={errors.price || ''}
                    onChange={(e) => update('price', e.target.value.replace(',', '.'))}
                    slotProps={{ htmlInput: { inputMode: 'decimal', 'data-testid': 'course-price-input' } }}
                />
                <Autocomplete
                    options={currencyOptions}
                    value={selectedCurrency}
                    disabled={readOnly}
                    onChange={(_, option) => update('currency', option ? option.code : '')}
                    getOptionLabel={(option) => option.label}
                    isOptionEqualToValue={(option, selected) => option.code === selected.code}
                    renderInput={(params) => (
                        <TextField
                            {...params}
                            label={localeMessages['course_price_currency']}
                            margin="normal"
                            error={Boolean(errors.currency)}
                            helperText={errors.currency || ''}
                        />
                    )}
                />
            </Box>
            <TextField
                label={localeMessages['course_price_subtitle']}
                fullWidth
                margin="normal"
                value={value.subtitle}
                disabled={readOnly}
                onChange={(e) => update('subtitle', e.target.value)}
                helperText={localeMessages['course_price_subtitle_helper_text']}
                slotProps={{ htmlInput: { maxLength: PRICE_SUBTITLE_MAX_LENGTH } }}
                dir={direction}
            />
        </Box>
    );
}
