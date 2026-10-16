// Same limits as Course.price: up to 8 digits before the decimal point and 2 after.
export const PRICE_PATTERN = /^\d{1,8}(\.\d{1,2})?$/;
export const PRICE_SUBTITLE_MAX_LENGTH = 200;

export const EMPTY_PRICE_SETTINGS = { price: '', currency: '', subtitle: '' };

export const priceSettingsFrom = (data) => ({
    price: data.price ?? '',
    currency: data.price_currency || '',
    subtitle: data.price_subtitle || '',
});

/** Error messages for the price fields, keyed like the settings; empty when they are valid. */
export const validatePriceSettings = ({ price, currency, subtitle }, localeMessages) => {
    const errors = {};
    const amount = price.trim();
    if (amount && !PRICE_PATTERN.test(amount)) {
        errors.price = localeMessages['course_price_invalid'];
    }
    if (amount && !currency) {
        errors.currency = localeMessages['course_price_currency_required'];
    }
    if (!amount && subtitle.trim()) {
        errors.price = localeMessages['course_price_requires_amount'];
    }
    return errors;
};

/** The fields of the price settings to send in an update: only what changed, with null clearing. */
export const priceUpdate = (current, initial) => {
    const update = {};
    const amount = current.price.trim();
    if (amount !== initial.price) {
        update.price = amount || null;
    }
    if (current.currency !== initial.currency) {
        update.price_currency = current.currency || null;
    }
    if (current.subtitle.trim() !== initial.subtitle) {
        update.price_subtitle = current.subtitle.trim() || null;
    }
    return update;
};
