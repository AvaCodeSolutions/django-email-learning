import { useEffect, useRef, useState } from 'react';
import { IconButton, Stack, Tooltip, Typography } from '@mui/material';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import ShareIcon from '@mui/icons-material/Share';
import { buildShareLinks } from './shareLinks.js';

const COPIED_FEEDBACK_MS = 2000;

function ShareButtons({ url, title, messages, label }) {
    const [copied, setCopied] = useState(false);
    const copiedTimer = useRef(null);
    const canNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';
    const canCopy = typeof navigator !== 'undefined' && Boolean(navigator.clipboard?.writeText);

    useEffect(() => () => clearTimeout(copiedTimer.current), []);

    if (!url) {
        return null;
    }

    const copyLink = async () => {
        try {
            await navigator.clipboard.writeText(url);
        } catch {
            return;
        }
        setCopied(true);
        clearTimeout(copiedTimer.current);
        copiedTimer.current = setTimeout(() => setCopied(false), COPIED_FEEDBACK_MS);
    };

    const nativeShare = async () => {
        try {
            await navigator.share({ title, url });
        } catch {
            // Dismissing the share sheet rejects; nothing to do.
        }
    };

    const iconButtonSx = { color: 'text.secondary', '&:hover': { color: 'text.primary' } };
    const shareOn = (name) => (messages['share_on'] || 'Share on PLATFORM').replace('PLATFORM', name);
    const copyLabel = copied ? messages['link_copied'] || 'Link copied' : messages['copy_link'] || 'Copy link';
    const emailLabel = messages['share_by_email'] || 'Share by email';
    const moreLabel = messages['more_share_options'] || 'More options';

    return (
        <Stack spacing={0.5}>
            {label && (
                <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 500 }}>
                    {label}
                </Typography>
            )}
            <Stack direction="row" sx={{ flexWrap: 'wrap', mx: -1 }}>
                {buildShareLinks(url, title).map(({ key, name, icon: NetworkIcon, href }) => (
                    <Tooltip key={key} title={shareOn(name)}>
                        <IconButton
                            component="a"
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={shareOn(name)}
                            size="small"
                            sx={iconButtonSx}
                        >
                            <NetworkIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                ))}
                <Tooltip title={emailLabel}>
                    <IconButton
                        component="a"
                        href={`mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`}
                        aria-label={emailLabel}
                        size="small"
                        sx={iconButtonSx}
                    >
                        <EmailOutlinedIcon fontSize="small" />
                    </IconButton>
                </Tooltip>
                {canCopy && (
                    <Tooltip title={copyLabel}>
                        <IconButton onClick={copyLink} aria-label={copyLabel} size="small" sx={iconButtonSx}>
                            {copied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
                        </IconButton>
                    </Tooltip>
                )}
                {canNativeShare && (
                    <Tooltip title={moreLabel}>
                        <IconButton onClick={nativeShare} aria-label={moreLabel} size="small" sx={iconButtonSx}>
                            <ShareIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                )}
            </Stack>
        </Stack>
    );
}

export default ShareButtons;
