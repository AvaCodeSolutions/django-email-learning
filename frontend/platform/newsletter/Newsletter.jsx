import 'vite/modulepreload-polyfill'
import { useState, useEffect } from 'react';
import { styled } from '@mui/material/styles';
import Base from '../../src/components/Base.jsx';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import DialogContentText from '@mui/material/DialogContentText';
import LinearProgress from '@mui/material/LinearProgress';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Tooltip from '@mui/material/Tooltip';
import { Tabs, Tab, InputAdornment, GlobalStyles } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ScheduleIcon from '@mui/icons-material/Schedule';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import ListIcon from '@mui/icons-material/List';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import CodeIcon from '@mui/icons-material/Code';
import ContentEditor from '../../src/components/ContentEditor.jsx';
import EmbedCodeBlock from '../../src/components/EmbedCodeBlock.jsx';
import apiClient from '../../src/apiClient.js';
import render, { useAppContext } from '../../src/render.jsx';
import Coloris from '@melloware/coloris';
import '@melloware/coloris/dist/coloris.css';

const VisuallyHiddenInput = styled('input')({
    clip: 'rect(0 0 0 0)',
    clipPath: 'inset(50%)',
    height: 1,
    overflow: 'hidden',
    position: 'absolute',
    bottom: 0,
    left: 0,
    whiteSpace: 'nowrap',
    width: 1,
});

function toLocalDatetimeValue(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function defaultScheduledAt() {
    const d = new Date();
    d.setHours(d.getHours() + 1, 0, 0, 0);
    return toLocalDatetimeValue(d.toISOString());
}

function SendoutDialog({ open, onClose, onSuccess, sendout, newsletterId, organizationId, localeMessages, apiBaseUrl, direction }) {
    const isEdit = Boolean(sendout);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [scheduledAt, setScheduledAt] = useState('');
    const [error, setError] = useState('');
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(false);
    const [editorInstance, setEditorInstance] = useState(null);
    const [uploadedImages, setUploadedImages] = useState([]);
    const [imageUploadError, setImageUploadError] = useState('');
    const [imagePendingDelete, setImagePendingDelete] = useState(null);
    const [deleteImageDialogOpen, setDeleteImageDialogOpen] = useState(false);
    const [isDeletingImage, setIsDeletingImage] = useState(false);

    useEffect(() => {
        if (!open) return;
        setUploadedImages([]);
        setImageUploadError('');
        if (isEdit) {
            setLoading(true);
            apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/sendouts/${sendout.id}/`)
                .then(data => {
                    setSubject(data.subject);
                    setBody(data.body);
                    setScheduledAt(toLocalDatetimeValue(data.scheduled_at));
                })
                .catch(() => setError(localeMessages['sendout_create_error']))
                .finally(() => setLoading(false));
        } else {
            setSubject('');
            setBody('');
            setScheduledAt(defaultScheduledAt());
            setError('');
        }
    }, [open, sendout]);

    const handleSave = () => {
        if (!subject.trim()) { setError(localeMessages['sendout_subject_required']); return; }
        if (!body.trim()) { setError(localeMessages['sendout_body_required']); return; }
        if (!scheduledAt) { setError(localeMessages['sendout_scheduled_at_required']); return; }
        setSaving(true);
        const payload = { subject, body, scheduled_at: new Date(scheduledAt).toISOString() };
        const req = isEdit
            ? apiClient.patch(`${apiBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/sendouts/${sendout.id}/`, payload)
            : apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/sendouts/`, payload);
        req.then(() => {
            setSaving(false);
            onSuccess();
        }).catch(() => {
            setSaving(false);
            setError(localeMessages['sendout_create_error']);
        });
    };

    const handleClose = () => {
        setError('');
        onClose();
    };

    const handleImageUpload = (event) => {
        const selectedFile = event.target.files?.[0];
        if (!selectedFile) return;
        const isImage = selectedFile.type.startsWith('image/');
        const isWebp = selectedFile.type === 'image/webp' || selectedFile.name.toLowerCase().endsWith('.webp');
        if (!isImage || isWebp) {
            setImageUploadError('Only non-WebP image files are allowed.');
            event.target.value = '';
            return;
        }
        setImageUploadError('');
        const formData = new FormData();
        formData.append('file', selectedFile);
        apiClient.upload(`${apiBaseUrl}/organizations/${organizationId}/files/`, formData)
            .then(data => { setUploadedImages(prev => [...prev, data]); event.target.value = ''; })
            .catch(() => setImageUploadError('Image upload failed. Please try again.'));
    };

    const normalizeUrl = (url) => {
        if (!url) return '';
        try {
            const p = new URL(url, window.location.origin);
            return `${p.origin}${p.pathname}`.toLowerCase();
        } catch {
            return String(url).trim().toLowerCase();
        }
    };

    const isImageUsedInEditor = (imageUrl) => {
        const html = editorInstance?.getHTML?.() || body || '';
        if (!html) return false;
        const target = normalizeUrl(imageUrl);
        if (!target) return false;
        try {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            return Array.from(doc.querySelectorAll('img'))
                .map(img => normalizeUrl(img.getAttribute('src')))
                .filter(Boolean)
                .includes(target);
        } catch {
            return html.includes(imageUrl);
        }
    };

    const requestRemoveImage = (image) => {
        if (!image?.file_url) return;
        if (isImageUsedInEditor(image.file_url)) {
            setImageUploadError(localeMessages['uploaded_image_used_in_editor_error']);
            return;
        }
        setImageUploadError('');
        setImagePendingDelete(image);
        setDeleteImageDialogOpen(true);
    };

    const confirmRemoveImage = () => {
        if (!imagePendingDelete?.file_path) {
            setDeleteImageDialogOpen(false);
            setImagePendingDelete(null);
            setImageUploadError(localeMessages['uploaded_image_delete_failed']);
            return;
        }
        setIsDeletingImage(true);
        apiClient.del(`${apiBaseUrl}/organizations/${organizationId}/files/`, {
            file_path: imagePendingDelete.file_path,
            file_url: imagePendingDelete.file_url,
        })
            .then(() => {
                setUploadedImages(prev => prev.filter(img => img.file_url !== imagePendingDelete.file_url));
                setDeleteImageDialogOpen(false);
                setImagePendingDelete(null);
                setImageUploadError('');
            })
            .catch(() => setImageUploadError(localeMessages['uploaded_image_delete_failed']))
            .finally(() => setIsDeletingImage(false));
    };

    const addImageToEditor = (imageUrl) => {
        if (!editorInstance || !imageUrl) return;
        editorInstance.chain().focus().setImage({ src: imageUrl }).run();
    };

    const title = isEdit ? sendout?.subject : localeMessages['create_sendout'];

    return (
        <>
            <Dialog open={open} onClose={handleClose} fullWidth maxWidth="lg">
                <DialogTitle>{title}</DialogTitle>
                <DialogContent>
                    {loading && <LinearProgress sx={{ mb: 2 }} />}
                    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                    <TextField
                        label={localeMessages['sendout_subject']}
                        value={subject}
                        onChange={e => setSubject(e.target.value)}
                        fullWidth
                        required
                        sx={{ mt: 1, mb: 2 }}
                    />
                    <TextField
                        label={localeMessages['sendout_scheduled_at']}
                        type="datetime-local"
                        value={scheduledAt}
                        onChange={e => setScheduledAt(e.target.value)}
                        fullWidth
                        required
                        sx={{ mb: 2 }}
                        slotProps={{ inputLabel: { shrink: true } }}
                    />
                    <Box sx={{ mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">{localeMessages['sendout_body']}</Typography>
                    </Box>
                    {!loading && (
                        <ContentEditor
                            key={open ? (sendout?.id ?? 'new') : 'closed'}
                            initialContent={body}
                            contentUpdateCallback={setBody}
                            extraMinLines={8}
                            defaultDirection={direction}
                            editorInstanceCallback={setEditorInstance}
                        />
                    )}

                    <Box sx={{ mt: 3 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>{localeMessages['upload_images']}</Typography>
                        {imageUploadError && <Alert severity="error" sx={{ mb: 1 }}>{imageUploadError}</Alert>}
                        <Button component="label" variant="outlined" sx={{ mb: 1.5 }}>
                            {localeMessages['upload']}
                            <VisuallyHiddenInput
                                type="file"
                                accept="image/png,image/jpeg,image/gif,image/bmp,image/svg+xml,image/tiff,image/avif"
                                onChange={handleImageUpload}
                            />
                        </Button>
                        <Box sx={{ border: '1px solid', borderColor: 'border.main', borderRadius: 1, p: 1.25, backgroundColor: 'background.box' }}>
                            {uploadedImages.length === 0 ? (
                                <Typography variant="body2" color="text.secondary">{localeMessages['no_uploaded_images']}</Typography>
                            ) : (
                                uploadedImages.map((image, index) => (
                                    <Box key={`${image.file_url}-${index}`} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 0.5, gap: 1 }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, flex: 1 }}>
                                            <Box
                                                component="img"
                                                src={image.file_url}
                                                alt={localeMessages['uploaded_image_preview']}
                                                sx={{ width: 47, height: 47, borderRadius: 0.5, objectFit: 'contain', border: '1px solid', borderColor: 'border.main', flexShrink: 0 }}
                                            />
                                            <Link href={image.file_url} target="_blank" rel="noopener noreferrer" sx={{ wordBreak: 'break-all', minWidth: 0 }}>
                                                {image.file_url}
                                            </Link>
                                        </Box>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
                                            <IconButton aria-label={localeMessages['add_image_to_editor']} onClick={() => addImageToEditor(image.file_url)} size="small">
                                                <AddIcon fontSize="small" />
                                            </IconButton>
                                            <IconButton aria-label={localeMessages['remove_uploaded_image']} onClick={() => requestRemoveImage(image)} size="small">
                                                <DeleteIcon fontSize="small" />
                                            </IconButton>
                                        </Box>
                                    </Box>
                                ))
                            )}
                        </Box>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose} variant="outlined">{localeMessages['cancel']}</Button>
                    <Button onClick={handleSave} variant="contained" disabled={saving || loading}>{localeMessages['save']}</Button>
                </DialogActions>
            </Dialog>

            <Dialog open={deleteImageDialogOpen} onClose={() => setDeleteImageDialogOpen(false)} maxWidth="xs" fullWidth>
                <DialogTitle>{localeMessages['confirm_delete_uploaded_image']}</DialogTitle>
                <DialogContent>
                    <DialogContentText>{localeMessages['delete_uploaded_image_warning']}</DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteImageDialogOpen(false)} variant="outlined" disabled={isDeletingImage}>{localeMessages['cancel']}</Button>
                    <Button onClick={confirmRemoveImage} variant="contained" color="error" disabled={isDeletingImage}>{localeMessages['delete'] || 'Delete'}</Button>
                </DialogActions>
            </Dialog>
        </>
    );
}

function Newsletter() {
    const { newsletterId, newsletterTitle, organizationId, localeMessages, direction, isOrganizationAdmin, apiBaseUrl, platformBaseUrl, embeddableEnrollmentEnabled } = useAppContext();
    const [sendouts, setSendouts] = useState([]);
    const [activeTab, setActiveTab] = useState('scheduled');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedSendout, setSelectedSendout] = useState(null);
    const [deletingSendout, setDeletingSendout] = useState(null);
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [deleteError, setDeleteError] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);
    const [embedDialogOpen, setEmbedDialogOpen] = useState(false);
    const [embedScriptHtml, setEmbedScriptHtml] = useState(null);
    const [embedWidgetHtml, setEmbedWidgetHtml] = useState(null);
    const [embedSnippetLoading, setEmbedSnippetLoading] = useState(false);
    const [embedSnippetError, setEmbedSnippetError] = useState(false);
    const [embedScriptCopied, setEmbedScriptCopied] = useState(false);
    const [embedWidgetCopied, setEmbedWidgetCopied] = useState(false);
    const [buttonBgColor, setButtonBgColor] = useState('#4f46e5');
    const [buttonTextColor, setButtonTextColor] = useState('#ffffff');
    const theme = useTheme();

    const fetchSendouts = (status) => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/sendouts/?status=${status}`)
            .then(data => setSendouts(data.sendouts))
            .catch(err => console.error('Error fetching sendouts:', err));
    };

    useEffect(() => {
        fetchSendouts(activeTab);
    }, [activeTab]);

    const openCreate = () => { setSelectedSendout(null); setDialogOpen(true); };
    const openEdit = (s) => { setSelectedSendout(s); setDialogOpen(true); };
    const handleClose = () => setDialogOpen(false);
    const handleSuccess = () => { setDialogOpen(false); fetchSendouts(activeTab); };

    const requestDeleteSendout = (s) => { setDeletingSendout(s); setDeleteError(''); setDeleteConfirmOpen(true); };
    const cancelDelete = () => { setDeleteConfirmOpen(false); setDeletingSendout(null); setDeleteError(''); };
    const confirmDelete = () => {
        if (!deletingSendout) return;
        setIsDeleting(true);
        apiClient.del(`${apiBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/sendouts/${deletingSendout.id}/`)
            .then(() => { setDeleteConfirmOpen(false); setDeletingSendout(null); fetchSendouts(activeTab); })
            .catch(() => setDeleteError(localeMessages['sendout_delete_error'] || 'Failed to delete sendout.'))
            .finally(() => setIsDeleting(false));
    };

    const handleOpenEmbedDialog = () => {
        setEmbedDialogOpen(true);
        if (embedWidgetHtml || embedSnippetLoading) {
            return;
        }
        setEmbedSnippetLoading(true);
        setEmbedSnippetError(false);
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/embed_snippet/`)
            .then(data => {
                setEmbedScriptHtml(data.script_html);
                setEmbedWidgetHtml(data.widget_html);
            })
            .catch(error => {
                console.error('Failed to load embed snippet:', error);
                setEmbedSnippetError(true);
            })
            .finally(() => setEmbedSnippetLoading(false));
    };

    const handleCloseEmbedDialog = () => {
        setEmbedDialogOpen(false);
    };

    // Loads the shared del-enroll-form/del-newsletter-form custom element
    // definitions (idempotent - the script itself no-ops if already defined)
    // so the preview below the embed code can render the widget exactly as
    // it'll look on the org's own site.
    useEffect(() => {
        if (!embedScriptHtml) {
            return;
        }
        const scriptSrc = embedScriptHtml.match(/src="([^"]+)"/)?.[1];
        if (!scriptSrc || document.querySelector(`script[src="${scriptSrc}"]`)) {
            return;
        }
        const script = document.createElement('script');
        script.src = scriptSrc;
        document.head.appendChild(script);
    }, [embedScriptHtml]);

    // Sets up the two color-picker inputs below. Runs once - Coloris attaches
    // itself to any current/future element matching the selector, so it
    // doesn't need to re-run when the dialog opens/closes.
    useEffect(() => {
        Coloris.init();
        Coloris({
            el: '.coloris-input',
            // MUI's TextField already manages the input's surrounding DOM via
            // React; letting Coloris also wrap the field and inject its own
            // swatch button fights that on every re-render (breaks the
            // picker, throws off alignment). We show our own swatch instead
            // (see the InputAdornment below).
            wrap: false,
            theme: 'polaroid',
            alpha: false,
            format: 'hex',
            onChange: (color, currentEl) => {
                if (currentEl?.id === 'newsletter-embed-button-bg-color') {
                    setButtonBgColor(color);
                } else if (currentEl?.id === 'newsletter-embed-button-text-color') {
                    setButtonTextColor(color);
                }
            },
        });
    }, []);

    const displayedEmbedWidgetHtml = (() => {
        if (!embedWidgetHtml) {
            return embedWidgetHtml;
        }
        const escapedBg = buttonBgColor.replace(/"/g, '&quot;');
        const escapedText = buttonTextColor.replace(/"/g, '&quot;');
        return embedWidgetHtml.replace(
            '<del-newsletter-form ',
            `<del-newsletter-form button_bg_color="${escapedBg}" button_text_color="${escapedText}" `,
        );
    })();

    const embedWidgetPreviewHtml = displayedEmbedWidgetHtml?.replace('<del-newsletter-form ', '<del-newsletter-form preview ');

    const handleCopyEmbedScript = async () => {
        try {
            await navigator.clipboard.writeText(embedScriptHtml);
            setEmbedScriptCopied(true);
            setTimeout(() => setEmbedScriptCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy embed script:', error);
        }
    };

    const handleCopyEmbedWidget = async () => {
        try {
            await navigator.clipboard.writeText(displayedEmbedWidgetHtml);
            setEmbedWidgetCopied(true);
            setTimeout(() => setEmbedWidgetCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy embed widget tag:', error);
        }
    };

    const formatDate = (isoString) => {
        if (!isoString) return '—';
        return new Date(isoString).toLocaleString();
    };

    const statusLabel = (status) => localeMessages[status] || status;

    const subjectLinkSx = {
        cursor: 'pointer',
        color: theme.palette.mode === 'dark'
            ? theme.palette.link?.main ?? theme.palette.primary.light
            : theme.palette.primary.dark,
        '&:hover': { opacity: 0.8 },
    };

    return (
        <Base
            breadCrumbList={[
                { label: localeMessages['organizations'] || 'Organizations', href: `${platformBaseUrl}/organizations`, index: 0 },
                { label: localeMessages['newsletters'] || 'Newsletters', href: `${platformBaseUrl}/organizations/${organizationId}/?tab=newsletters`, index: 1 },
                { label: newsletterTitle, href: '#', index: 2 },
            ]}
            showOrganizationSwitcher={false}
        >
            <Grid size={12} sx={{ py: 2, px: { xs: 0, sm: 4 } }}>
                <Box sx={{ backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', borderRadius: { xs: 0, sm: 2 }, minHeight: 300 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: { xs: 1, sm: 2 }, pt: 2 }}>
                        <Tabs
                            value={activeTab}
                            onChange={(_, value) => setActiveTab(value)}
                            variant="scrollable"
                            scrollButtons="auto"
                        >
                            <Tab value="scheduled" icon={<ScheduleIcon fontSize="small" />} iconPosition="start" label={localeMessages['scheduled']} />
                            <Tab value="sent" icon={<DoneAllIcon fontSize="small" />} iconPosition="start" label={localeMessages['sent']} />
                            <Tab value="all" icon={<ListIcon fontSize="small" />} iconPosition="start" label={localeMessages['all']} />
                        </Tabs>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            {embeddableEnrollmentEnabled && (
                                <Button variant="outlined" startIcon={<CodeIcon fontSize="small" />} onClick={handleOpenEmbedDialog}>
                                    {localeMessages['add_to_your_site']}
                                </Button>
                            )}
                            <Button variant="outlined" href={`${platformBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/subscribers/`}>
                                {localeMessages['newsletter_subscribers']}
                            </Button>
                            {isOrganizationAdmin && (
                                <Button variant="contained" color="secondary" onClick={openCreate}>
                                    {localeMessages['create_sendout']}
                                </Button>
                            )}
                        </Box>
                    </Box>

                    <Box sx={{ p: { xs: 1, sm: 2 }, borderTop: 1, borderColor: 'divider' }}>
                        {sendouts.length > 0 ? (
                            <TableContainer>
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>{localeMessages['subject']}</TableCell>
                                            <TableCell>{localeMessages['scheduled_at']}</TableCell>
                                            <TableCell>{localeMessages['status']}</TableCell>
                                            {isOrganizationAdmin && <TableCell />}
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {sendouts.map(s => (
                                            <TableRow key={s.id}>
                                                <TableCell>
                                                    <Box component="span" onClick={() => openEdit(s)} sx={subjectLinkSx}>
                                                        {s.subject}
                                                    </Box>
                                                </TableCell>
                                                <TableCell>{formatDate(s.scheduled_at)}</TableCell>
                                                <TableCell>
                                                    <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
                                                        {statusLabel(s.status)}
                                                        {s.status === 'blocked' && (
                                                            <Tooltip title={localeMessages['sendout_blocked_default_message'] || 'This sendout was blocked.'}>
                                                                <InfoOutlinedIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                                                            </Tooltip>
                                                        )}
                                                    </Box>
                                                </TableCell>
                                                {isOrganizationAdmin && (
                                                    <TableCell align="right">
                                                        {s.status !== 'sent' && (
                                                            <IconButton
                                                                aria-label={localeMessages['delete_sendout'] || 'Delete sendout'}
                                                                size="small"
                                                                onClick={() => requestDeleteSendout(s)}
                                                            >
                                                                <DeleteIcon fontSize="small" />
                                                            </IconButton>
                                                        )}
                                                    </TableCell>
                                                )}
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        ) : (
                            <Typography variant="body1">{localeMessages['no_sendouts']}</Typography>
                        )}
                    </Box>
                </Box>
            </Grid>

            <SendoutDialog
                open={dialogOpen}
                onClose={handleClose}
                onSuccess={handleSuccess}
                sendout={selectedSendout}
                newsletterId={newsletterId}
                organizationId={organizationId}
                localeMessages={localeMessages}
                apiBaseUrl={apiBaseUrl}
                direction={direction}
            />

            <Dialog open={deleteConfirmOpen} onClose={cancelDelete} maxWidth="xs" fullWidth>
                <DialogTitle>{localeMessages['confirm_delete_sendout'] || 'Delete sendout?'}</DialogTitle>
                <DialogContent>
                    {deleteError && <Alert severity="error" sx={{ mb: 1 }}>{deleteError}</Alert>}
                    <DialogContentText>
                        {localeMessages['delete_sendout_warning'] || 'This action cannot be undone. Are you sure you want to delete this sendout?'}
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={cancelDelete} variant="outlined" disabled={isDeleting}>{localeMessages['cancel']}</Button>
                    <Button onClick={confirmDelete} variant="contained" color="error" disabled={isDeleting}>{localeMessages['delete'] || 'Delete'}</Button>
                </DialogActions>
            </Dialog>

            {/* Coloris's popup defaults to a lower z-index than MUI's Dialog
                (1300), so without this it opens invisibly behind the dialog. */}
            <GlobalStyles styles={{ '.clr-picker': { zIndex: 1400 } }} />

            <Dialog open={embedDialogOpen} onClose={handleCloseEmbedDialog} fullWidth maxWidth="sm">
                {!embedSnippetLoading && !embedSnippetError && embedWidgetHtml && (
                    <Box sx={{ px: 3, pt: 3 }}>
                        <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                            {localeMessages['embed_preview_title']}
                        </Typography>
                        <Box
                            sx={{
                                p: 2,
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 1,
                                pointerEvents: 'none',
                                display: 'flex',
                                justifyContent: 'center',
                            }}
                            aria-hidden="true"
                            dangerouslySetInnerHTML={{ __html: embedWidgetPreviewHtml }}
                        />
                    </Box>
                )}
                <DialogTitle>{localeMessages['embed_customize_form_title']}</DialogTitle>
                <DialogContent>
                    {!embedSnippetLoading && !embedSnippetError && embedWidgetHtml && (
                        <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
                            <TextField
                                id="newsletter-embed-button-bg-color"
                                label={localeMessages['embed_button_bg_color_label']}
                                value={buttonBgColor}
                                onChange={(event) => setButtonBgColor(event.target.value)}
                                size="small"
                                sx={{ mt: '12px' }}
                                slotProps={{
                                    htmlInput: { className: 'coloris-input' },
                                    input: {
                                        startAdornment: (
                                            <InputAdornment position="start">
                                                <Box
                                                    sx={{
                                                        width: 18,
                                                        height: 18,
                                                        borderRadius: '4px',
                                                        border: '1px solid',
                                                        borderColor: 'divider',
                                                        backgroundColor: buttonBgColor,
                                                    }}
                                                />
                                            </InputAdornment>
                                        ),
                                    },
                                }}
                            />
                            <TextField
                                id="newsletter-embed-button-text-color"
                                label={localeMessages['embed_button_text_color_label']}
                                value={buttonTextColor}
                                onChange={(event) => setButtonTextColor(event.target.value)}
                                size="small"
                                slotProps={{
                                    htmlInput: { className: 'coloris-input' },
                                    input: {
                                        startAdornment: (
                                            <InputAdornment position="start">
                                                <Box
                                                    sx={{
                                                        width: 18,
                                                        height: 18,
                                                        borderRadius: '4px',
                                                        border: '1px solid',
                                                        borderColor: 'divider',
                                                        backgroundColor: buttonTextColor,
                                                    }}
                                                />
                                            </InputAdornment>
                                        ),
                                    },
                                }}
                            />
                        </Box>
                    )}
                    <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                        {localeMessages['embed_code_dialog_title']}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {localeMessages['embed_code_dialog_description']}
                    </Typography>
                    {embedSnippetLoading && (
                        <Box sx={{ py: 2 }}>
                            <LinearProgress />
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                {localeMessages['embed_code_loading']}
                            </Typography>
                        </Box>
                    )}
                    {!embedSnippetLoading && embedSnippetError && (
                        <Alert severity="error">{localeMessages['embed_code_error']}</Alert>
                    )}
                    {!embedSnippetLoading && !embedSnippetError && embedWidgetHtml && (
                        <>
                            <EmbedCodeBlock
                                label={localeMessages['embed_script_step_title']}
                                code={embedScriptHtml}
                                copied={embedScriptCopied}
                                onCopy={handleCopyEmbedScript}
                                copyLabel={localeMessages['copy_embed_script']}
                                copiedLabel={localeMessages['embed_code_copied']}
                            />
                            <EmbedCodeBlock
                                label={localeMessages['embed_widget_step_title']}
                                code={displayedEmbedWidgetHtml}
                                copied={embedWidgetCopied}
                                onCopy={handleCopyEmbedWidget}
                                copyLabel={localeMessages['copy_embed_widget']}
                                copiedLabel={localeMessages['embed_code_copied']}
                            />
                        </>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseEmbedDialog}>{localeMessages['close']}</Button>
                </DialogActions>
            </Dialog>
        </Base>
    );
}

render({ children: <Newsletter /> });

export default Newsletter;
