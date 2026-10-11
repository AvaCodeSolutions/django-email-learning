export const slugify = (value) => {
    return value
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 50);
}

export const setCookie = (name, value, days = 365) => {
    const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

const MIN_CONTRAST = 4.5; // WCAG AA for normal-size text

const parseHex = (hexColor) => {
    const hex = (hexColor || '').replace('#', '');
    const full = hex.length === 3 ? hex.split('').map((c) => c + c).join('') : hex;
    if (full.length !== 6 || /[^0-9a-fA-F]/.test(full)) {
        return null;
    }
    return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
};

const luminance = (channels) => {
    const [r, g, b] = channels.map((channel) => {
        const value = channel / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

const contrast = (first, second) => {
    const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a);
    return (lighter + 0.05) / (darker + 0.05);
};

// Dark or light text, whichever has the higher WCAG contrast on `hexColor`.
export const getReadableTextColor = (hexColor, darkText = '#232936', lightText = '#ffffff') => {
    const background = parseHex(hexColor);
    if (!background) {
        return lightText;
    }
    return contrast(background, parseHex(darkText)) > contrast(background, parseHex(lightText)) ? darkText : lightText;
}

// A button's fill and text colour with at least 4.5:1 between them. Mirrors
// `button_colors()` in django_email_learning/services/email_buttons.py, so the editor
// draws a button exactly as the email will: when neither text colour reaches 4.5:1 on
// the brand colour, the fill moves 5% at a time towards black (under white text) or
// white (under dark text) until one does.
export const getButtonColors = (hexColor) => {
    const background = parseHex(hexColor);
    if (!background) {
        return { background: hexColor, text: '#ffffff' };
    }
    const text = getReadableTextColor(hexColor);
    const textChannels = parseHex(text);
    const target = text === '#ffffff' ? 0 : 255;
    let fill = background;
    for (let step = 1; contrast(fill, textChannels) < MIN_CONTRAST; step += 1) {
        const mix = step / 20;
        fill = background.map((channel) => Math.floor(channel + (target - channel) * mix + 0.5));
    }
    const toHex = (channels) => `#${channels.map((c) => c.toString(16).padStart(2, '0')).join('')}`;
    return { background: fill === background ? hexColor : toHex(fill), text };
}

export const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
        }
        }
    }
    return cookieValue;
}
