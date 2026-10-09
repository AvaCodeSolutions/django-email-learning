import XIcon from '@mui/icons-material/X';
import LinkedInIcon from '@mui/icons-material/LinkedIn';
import FacebookIcon from '@mui/icons-material/Facebook';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import TelegramIcon from '@mui/icons-material/Telegram';

// Plain share links rather than the networks' SDKs, so the public page loads
// no third-party scripts.
export function buildShareLinks(url, text) {
    const u = encodeURIComponent(url);
    const t = encodeURIComponent(text);
    return [
        { key: 'x', name: 'X', icon: XIcon, href: `https://x.com/intent/post?url=${u}&text=${t}` },
        { key: 'linkedin', name: 'LinkedIn', icon: LinkedInIcon, href: `https://www.linkedin.com/sharing/share-offsite/?url=${u}` },
        { key: 'facebook', name: 'Facebook', icon: FacebookIcon, href: `https://www.facebook.com/sharer/sharer.php?u=${u}` },
        { key: 'whatsapp', name: 'WhatsApp', icon: WhatsAppIcon, href: `https://wa.me/?text=${encodeURIComponent(`${text} ${url}`)}` },
        { key: 'telegram', name: 'Telegram', icon: TelegramIcon, href: `https://t.me/share/url?url=${u}&text=${t}` },
    ];
}
