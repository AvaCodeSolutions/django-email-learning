import 'vite/modulepreload-polyfill'
import { useState, useEffect, useCallback } from 'react';
import Base from '../../src/components/Base.jsx';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import DialogContentText from '@mui/material/DialogContentText';
import Grid from '@mui/material/Grid';
import IconButton from '@mui/material/IconButton';
import LinearProgress from '@mui/material/LinearProgress';
import Pagination from '@mui/material/Pagination';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import DeleteIcon from '@mui/icons-material/Delete';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import apiClient from '../../src/apiClient.js';
import render, { useAppContext } from '../../src/render.jsx';

const PAGE_SIZE = 30;

function NewsletterSubscribers() {
    const { newsletterId, newsletterTitle, organizationId, localeMessages, direction, isOrganizationAdmin, apiBaseUrl, platformBaseUrl } = useAppContext();

    const [subscribers, setSubscribers] = useState([]);
    const [count, setCount] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const [pendingDelete, setPendingDelete] = useState(null);
    const [deleting, setDeleting] = useState(false);

    const apiBase = `${apiBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/subscribers`;

    const fetchSubscribers = useCallback((p) => {
        setLoading(true);
        apiClient.get(`${apiBase}/?page=${p}&page_size=${PAGE_SIZE}`)
            .then(data => {
                setSubscribers(data.items);
                setCount(data.count);
            })
            .catch(err => console.error('Error fetching subscribers:', err))
            .finally(() => setLoading(false));
    }, [apiBase]);

    useEffect(() => {
        fetchSubscribers(page);
    }, [page]);

    const handleDeleteConfirm = () => {
        if (!pendingDelete) return;
        setDeleting(true);
        apiClient.del(`${apiBase}/${pendingDelete.id}/`)
            .then(() => {
                setPendingDelete(null);
                fetchSubscribers(page);
            })
            .catch(err => console.error('Error deleting subscriber:', err))
            .finally(() => setDeleting(false));
    };

    const formatDate = (isoString) => {
        if (!isoString) return '—';
        return new Date(isoString).toLocaleString();
    };

    const totalPages = Math.ceil(count / PAGE_SIZE);
    const csvUrl = `${apiBase}/export.csv`;

    return (
        <Base
            breadCrumbList={[
                { label: localeMessages['organizations'] || 'Organizations', href: `${platformBaseUrl}/organizations`, index: 0 },
                { label: localeMessages['newsletters'] || 'Newsletters', href: `${platformBaseUrl}/organizations/${organizationId}/?tab=newsletters`, index: 1 },
                { label: newsletterTitle, href: `${platformBaseUrl}/organizations/${organizationId}/newsletters/${newsletterId}/`, index: 2 },
                { label: localeMessages['subscribers'] || 'Subscribers', href: '#', index: 3 },
            ]}
            showOrganizationSwitcher={false}
        >
            <Grid size={12} sx={{ py: 2, px: { xs: 0, sm: 4 } }}>
                <Box sx={{ backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', borderRadius: { xs: 0, sm: 2 }, minHeight: 300 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: { xs: 1, sm: 2 }, pt: 2, pb: 1 }}>
                        <Typography variant="h6">
                            {localeMessages['subscribers']} {count > 0 && `(${count})`}
                        </Typography>
                        {isOrganizationAdmin && (
                            <Button
                                variant="outlined"
                                size="small"
                                startIcon={<FileDownloadIcon />}
                                href={csvUrl}
                            >
                                {localeMessages['export_csv']}
                            </Button>
                        )}
                    </Box>

                    {loading && <LinearProgress />}

                    <Box sx={{ px: { xs: 1, sm: 2 } }}>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>{localeMessages['email']}</TableCell>
                                    <TableCell>{localeMessages['subscribed_at']}</TableCell>
                                    <TableCell>{localeMessages['status']}</TableCell>
                                    {isOrganizationAdmin && <TableCell align="right">{localeMessages['actions']}</TableCell>}
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {subscribers.length === 0 && !loading ? (
                                    <TableRow>
                                        <TableCell colSpan={isOrganizationAdmin ? 4 : 3} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                                            {localeMessages['no_subscribers']}
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    subscribers.map(sub => (
                                        <TableRow key={sub.id} hover>
                                            <TableCell>{sub.email}</TableCell>
                                            <TableCell>{formatDate(sub.subscribed_at)}</TableCell>
                                            <TableCell>
                                                <Chip
                                                    size="small"
                                                    label={sub.is_confirmed ? localeMessages['confirmed'] : localeMessages['pending_confirmation']}
                                                    color={sub.is_confirmed ? 'success' : 'default'}
                                                    variant={sub.is_confirmed ? 'filled' : 'outlined'}
                                                />
                                            </TableCell>
                                            {isOrganizationAdmin && (
                                                <TableCell align="right">
                                                    <IconButton size="small" color="error" onClick={() => setPendingDelete(sub)} aria-label={localeMessages['delete']}>
                                                        <DeleteIcon fontSize="small" />
                                                    </IconButton>
                                                </TableCell>
                                            )}
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    </Box>

                    {totalPages > 1 && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                            <Pagination count={totalPages} page={page} onChange={(_, p) => setPage(p)} color="primary" />
                        </Box>
                    )}
                </Box>
            </Grid>

            <Dialog open={Boolean(pendingDelete)} onClose={() => setPendingDelete(null)}>
                <DialogTitle>{localeMessages['confirm_delete']}</DialogTitle>
                <DialogContent>
                    <DialogContentText>{localeMessages['delete_subscriber_warning']}</DialogContentText>
                    {pendingDelete && <Typography sx={{ mt: 1, fontWeight: 600 }}>{pendingDelete.email}</Typography>}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setPendingDelete(null)} disabled={deleting}>{localeMessages['cancel']}</Button>
                    <Button onClick={handleDeleteConfirm} color="error" disabled={deleting}>{localeMessages['delete']}</Button>
                </DialogActions>
            </Dialog>
        </Base>
    );
}

render({ children: <NewsletterSubscribers /> });

export default NewsletterSubscribers;
