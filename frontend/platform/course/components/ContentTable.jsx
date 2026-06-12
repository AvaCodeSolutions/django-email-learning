import { Alert, Box, CircularProgress, Chip, IconButton, Switch, TableContainer, Table, TableHead, TableRow, TableBody, TableCell, Paper, Tooltip, Typography } from '@mui/material';
import EmptyTableState from '../../../src/components/EmptyTableState.jsx';
import { useState, useEffect, useRef } from 'react';
import DeleteIcon from '@mui/icons-material/Delete';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import BallotOutlinedIcon from '@mui/icons-material/BallotOutlined';
import AssignmentOutlinedIcon from '@mui/icons-material/AssignmentOutlined';
import apiClient from '../../../src/apiClient.js';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ForwardToInboxOutlinedIcon from '@mui/icons-material/ForwardToInboxOutlined';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

import { useAppContext } from '../../../src/render.jsx';


const ContentTable = ({ courseId, eventHandler, loaded = false }) => {
    const [contentList, setContentList] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [draggedContentId, setDraggedContentId] = useState(null);
    const contentListRef = useRef(contentList);
    const draggedContentIdRef = useRef(draggedContentId);
    const [sendingContentId, setSendingContentId] = useState(null);
    const [sendSuccessMessage, setSendSuccessMessage] = useState('');

    const startDrag = (event, contentId) => {
        event.preventDefault();
        setIsDragging(true);
        setDraggedContentId(contentId);
        draggedContentIdRef.current = contentId;
    }

    const { apiBaseUrl, userRole, localeMessages, direction } = useAppContext();
    const organizationId = localStorage.getItem('activeOrganizationId');
    const canSendLesson = userRole === 'admin' || userRole === 'editor';
    const showQuizTwoAttemptNote = contentList.some((content) => content.type === 'quiz' && content.is_blocking !== false && content.limited_attempts == true);
    const showQuizUnlimitedAttemptsNote = contentList.some((content) => content.type === 'quiz' && content.is_blocking !== false && content.limited_attempts == false);

    const formatPeriod = (period) => {
        if (!period) {
            return "";
        }
        let unit = period.type;
        if (period.period === 1) {
            unit = period.type.slice(0, -1);
        }
        return `${period.period} ${unit}`;
    }

    useEffect(() => {
        if (!loaded) {
            getContets();
        }
    }, [loaded]);

    useEffect(() => {
        contentListRef.current = contentList;
    }, [contentList]);

    useEffect(() => {
        const onPointerUp = () => {
            setIsDragging(false);
            setDraggedContentId(null);
            draggedContentIdRef.current = null;
        };

        const onTouchMove = (e) => {
            if (!draggedContentIdRef.current) return;
            e.preventDefault();
            const touch = e.touches[0];
            const el = document.elementFromPoint(touch.clientX, touch.clientY);
            const row = el?.closest('[data-content-id]');
            if (!row) return;
            const hoverId = Number(row.dataset.contentId);
            const dragId = draggedContentIdRef.current;
            if (hoverId === dragId) return;
            const list = contentListRef.current;
            const draggedIndex = list.findIndex(c => c.id === dragId);
            const hoverIndex = list.findIndex(c => c.id === hoverId);
            if (draggedIndex === -1 || hoverIndex === -1) return;
            const newList = [...list];
            const [draggedItem] = newList.splice(draggedIndex, 1);
            newList.splice(hoverIndex, 0, draggedItem);
            contentListRef.current = newList;
            setContentList(newList);
            eventHandler({ type: 'content_reordered', new_order: newList.map(c => c.id) });
        };

        window.addEventListener('pointerup', onPointerUp);
        window.addEventListener('touchmove', onTouchMove, { passive: false });

        return () => {
            window.removeEventListener('pointerup', onPointerUp);
            window.removeEventListener('touchmove', onTouchMove);
        };
    }, []);

    useEffect(() => {
        window.ContentDialogAPI = {
            open: (id) => {
                if (contentList.some(content => content.id == id)) {
                    let event = {type: 'content_clicked', content_id: id};
                    eventHandler(event);
                } else {
                    console.warn(`Content with id ${id} not found in content list.`);
                }
            }
        };
    }, [contentList]);

    useEffect(() => {
        if (isDragging) {
            document.body.style.userSelect = 'none';
        } else {
            document.body.style.userSelect = '';
        }

        return () => {
            document.body.style.userSelect = '';
        };
    }, [isDragging]);

    useEffect(() => {
        if (!sendSuccessMessage) {
            return;
        }

        const timeoutId = window.setTimeout(() => {
            setSendSuccessMessage('');
        }, 4000);

        return () => {
            window.clearTimeout(timeoutId);
        };
    }, [sendSuccessMessage]);

    const deleteContent = (contentId) => {
        eventHandler({ type: 'delete_content', content: contentList.find(content => content.id === contentId)});
    }

    const TogglePublishContent = (contentId, is_published) => {
        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`, {
                is_published: is_published
        })
            .then(() => {
                console.log('Publish status toggled successfully');
                // Update the local state to reflect the change
                setContentList(contentList.map(content => {
                    if (content.id === contentId) {
                        return { ...content, is_published: !content.is_published };
                    }
                    return content;
                }));
            })
            .catch(error => console.error('Error toggling publish status:', error));
    }


    const getContets = () => {

        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents`)
            .then(data => {
                setContentList(data.course_contents);
                let event = {type: 'content_loaded', data: data};
                eventHandler(event);
            })
            .catch(error => console.error('Error fetching content list:', error));
    }

    const sendLessonToCurrentUser = (contentId) => {
        setSendingContentId(contentId);
        apiClient.post(`${apiBaseUrl}/organizations/${organizationId}/send-lesson/`, {
                id: contentId,
        })
            .then(() => {
                console.log('Lesson sent successfully');
                setSendSuccessMessage(localeMessages["lesson_sent_to_your_email"] || 'Lesson sent to your email.');
            })
            .catch((error) => {
                console.error('Error sending lesson:', error);
            })
            .finally(() => {
                setSendingContentId(null);
            });
    }

    return (
        <>
        {sendSuccessMessage && (
            <Alert severity="success" sx={{ mb: 1 }}>
                {sendSuccessMessage}
            </Alert>
        )}
          <TableContainer component={Paper} dir={direction} sx={{ borderRadius: { xs: 0, sm: '8px' }, borderLeft: { xs: '0 !important', sm: undefined }, borderRight: { xs: '0 !important', sm: undefined } }}>
              <Table size="small" sx={{ width: "100%", direction: direction }} aria-label="Contents">
            <TableHead sx={{ display: { xs: 'none', sm: 'table-header-group' } }}>
              <TableRow>
                { userRole !== 'viewer' && <TableCell sx={{ width: '40px', boxSizing: 'border-box' }}></TableCell>}
                <TableCell sx={{ textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["title"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["waiting_time"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["type"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["published"]}</TableCell>
                {userRole !== 'viewer' && <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={direction == 'rtl' ? 'right' : 'left'}>{localeMessages["actions"]}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
                {contentList.length === 0 && (
                  <EmptyTableState
                    colSpan={userRole !== 'viewer' ? 6 : 5}
                    message={localeMessages['no_content_found'] || 'No content added yet.'}
                  />
                )}
                {contentList.map((content) => (
                    <TableRow
                        key={content.id}
                        data-content-id={content.id}
                        sx={{
                            transition: 'transform 120ms ease, box-shadow 120ms ease, background-color 120ms ease',
                            ...(isDragging && draggedContentId === content.id
                                ? {
                                    backgroundColor: 'background.box',
                                    transform: 'translateY(-2px) scale(1.005)',
                                    filter: (theme) => theme.palette.mode === 'dark'
                                        ? 'drop-shadow(0 2px 4px rgba(0,0,0,0.22))'
                                        : 'drop-shadow(0 2px 4px rgba(16,24,40,0.08))',
                                    borderTop: '1px solid',
                                    borderBottom: '1px solid',
                                    borderColor: 'primary.main',
                                    '& > td': {
                                        backgroundColor: 'background.box',
                                    },
                                }
                                : {}
                            ),
                        }}
                        onMouseOver={() => {
                            if (isDragging && draggedContentId !== content.id) {
                                const draggedIndex = contentList.findIndex(c => c.id === draggedContentId);
                                const hoverIndex = contentList.findIndex(c => c.id === content.id);
                                const newContentList = [...contentList];
                                const [draggedItem] = newContentList.splice(draggedIndex, 1);
                                newContentList.splice(hoverIndex, 0, draggedItem);
                                setContentList(newContentList);
                                let event = {type: 'content_reordered', new_order: newContentList.map(content => content.id)};
                                console.log('Dispatching event:', event);
                                eventHandler(event);
                            }
                        }}>
                         { userRole !== 'viewer' && <TableCell align={direction == 'rtl' ? 'right' : 'left'} sx={{ cursor: 'grab', width: { xs: '48px', sm: '40px' }, minWidth: { xs: '48px', sm: '40px' }, padding: { xs: '8px 4px', sm: '8px 0' }, textAlign: 'center' }}><DragIndicatorIcon fontSize="small"
                        onMouseDown={(event) => startDrag(event, content.id)}
                        onTouchStart={(event) => startDrag(event, content.id)}
                        /></TableCell>}
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'} sx={{ position: 'relative', pl: { xs: 0.5, sm: 2 } }}>
                            {isDragging && draggedContentId === content.id && (
                                <Box sx={{
                                    display: { xs: 'flex', sm: 'none' },
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    position: 'absolute',
                                    right: 8,
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    backgroundColor: 'action.selected',
                                    borderRadius: 1,
                                    px: 0.25,
                                    py: 0.25,
                                }}>
                                    <KeyboardArrowUpIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                                    <KeyboardArrowDownIcon sx={{ fontSize: 16, color: 'text.secondary', mt: '-6px' }} />
                                </Box>
                            )}
                            <Box
                                component="span"
                                onClick={() => {let event = {type: 'content_clicked', content_id: content.id}; eventHandler(event);}}
                                sx={(theme) => ({ cursor: 'pointer', color: theme.palette.mode === 'dark' ? theme.palette.link?.main ?? theme.palette.primary.light : theme.palette.primary.dark, display: { xs: 'block', sm: 'inline-flex' }, alignItems: 'center', gap: 0.5, '&:hover': { opacity: 0.8 }, '&:hover .edit-icon': { opacity: 1 } })}>
                                <Box component="span" sx={{ display: { xs: 'inline-flex', sm: 'none' }, alignItems: 'center', gap: 0.4, color: 'text.secondary', fontWeight: 500, verticalAlign: 'middle', mr: 0.5 }}>
                                    {content.type === 'lesson' ? <DescriptionOutlinedIcon sx={{ fontSize: '0.95rem' }} /> : content.type === 'quiz' ? <BallotOutlinedIcon sx={{ fontSize: '0.95rem' }} /> : <AssignmentOutlinedIcon sx={{ fontSize: '0.95rem' }} />}
                                    {localeMessages[content.type]}:
                                </Box>
                                <Box component="span" sx={{ display: { xs: 'inline', sm: 'inline-flex' }, alignItems: 'center', gap: 0.5 }}>
                                    {content.title}
                                    {userRole !== 'viewer' && <EditOutlinedIcon className="edit-icon" sx={{ fontSize: '0.9rem', opacity: { xs: 1, sm: 0 }, transition: 'opacity 0.15s', verticalAlign: 'middle', ml: 1 }} />}
                                    {content.type === 'quiz' && content.is_blocking === false && (
                                        <Chip label={localeMessages["practice_quiz"]} size="small" sx={(theme) => ({ ml: 1, backgroundColor: theme.palette.mode === 'dark' ? 'rgba(33, 150, 243, 0.2)' : 'rgba(33, 150, 243, 0.14)', color: theme.palette.mode === 'dark' ? '#64B5F6' : '#0D47A1', fontSize: { xs: '0.6rem', sm: '0.75rem' }, height: { xs: 16, sm: 24 }, '& .MuiChip-label': { px: { xs: 0.5, sm: 1 } } })} />
                                    )}
                                </Box>
                            </Box>
                            {/* Mobile second line */}
                            <Box sx={{ display: { xs: 'flex', sm: 'none' }, alignItems: 'center', flexWrap: 'wrap', gap: 0, mt: 0.75 }}>
                                {formatPeriod(content.waiting_period) && (
                                    <>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, pl: 0, pr: 1 }}>
                                            <Typography variant="caption" color="text.disabled">{localeMessages["waiting_time"] || 'Delay'}:</Typography>
                                            <Typography variant="caption" color="text.secondary">{formatPeriod(content.waiting_period)}</Typography>
                                        </Box>
                                        <Box sx={{ width: '1px', height: '14px', backgroundColor: 'divider' }} />
                                    </>
                                )}
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, px: 1 }}>
                                    <Typography variant="caption" color="text.disabled">{localeMessages["published"] || 'Published'}:</Typography>
                                    <Switch size="small" checked={content.is_published} onChange={() => TogglePublishContent(content.id, !content.is_published)} disabled={userRole == 'viewer'} inputProps={{ 'aria-label': `${localeMessages["published"] || 'Published'}: ${content.title}` }} />
                                </Box>
                                {userRole !== 'viewer' && <>
                                    <Box sx={{ width: '1px', height: '14px', backgroundColor: 'divider' }} />
                                    <Box sx={{ display: 'flex', alignItems: 'center', px: 0.5 }}>
                                        <IconButton size="small" aria-label={localeMessages["delete"]} onClick={() => deleteContent(content.id)}><DeleteIcon fontSize="small" /></IconButton>
                                        {canSendLesson && content.type === 'lesson' && (
                                            sendingContentId === content.id ? (
                                                <CircularProgress size="16px" sx={{ display: 'inline-block', verticalAlign: 'middle', mx: '3px' }} />
                                            ) : (
                                                <Tooltip title={localeMessages["send_lesson_to_yourself"] || 'Send it to yourself'} placement="top">
                                                    <span>
                                                        <IconButton size="small" aria-label={localeMessages["send_lesson"] || 'Send lesson'} onClick={() => sendLessonToCurrentUser(content.id)}><ForwardToInboxOutlinedIcon fontSize="small" /></IconButton>
                                                    </span>
                                                </Tooltip>
                                            )
                                        )}
                                    </Box>
                                </>}
                            </Box>
                        </TableCell>
                        <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={direction == 'rtl' ? 'right' : 'left'}>{formatPeriod(content.waiting_period)}</TableCell>
                        <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={direction == 'rtl' ? 'right' : 'left'}>
                            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.5 }}>
                                <Chip
                                    size="small"
                                    icon={content.type === 'lesson' ? <DescriptionOutlinedIcon /> : content.type === 'quiz' ? <BallotOutlinedIcon /> : <AssignmentOutlinedIcon />}
                                    label={localeMessages[content.type]}
                                    variant="outlined"
                                    sx={(theme) => ({ fontSize: '0.75rem', color: theme.palette.mode === 'dark' ? theme.palette.text.primary : undefined, borderColor: theme.palette.mode === 'dark' ? theme.palette.text.secondary : undefined })}
                                />
                                {content.type === 'quiz' && content.is_blocking !== false && content.limited_attempts !== null && (
                                    <Chip
                                        size="small"
                                        variant="outlined"
                                        label={content.limited_attempts ? localeMessages["two_attempts"] : localeMessages["unlimited_attempts"]}
                                        sx={{ fontSize: '0.7rem', color: 'text.secondary', borderColor: 'divider' }}
                                    />
                                )}
                            </Box>
                        </TableCell>
                        <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={direction == 'rtl' ? 'right' : 'left'}><Switch checked={content.is_published} onChange={() => TogglePublishContent(content.id, !content.is_published)} disabled={userRole == 'viewer'} inputProps={{ 'aria-label': `${localeMessages["published"] || 'Published'}: ${content.title}` }} /></TableCell>
                        {userRole !== 'viewer' && <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={direction == 'rtl' ? 'right' : 'left'}>
                            <IconButton aria-label={localeMessages["delete"]} onClick={() => deleteContent(content.id)}><DeleteIcon /></IconButton>
                            {canSendLesson && content.type === 'lesson' && (
                                sendingContentId === content.id ? (
                                    <CircularProgress size="18px" sx={{ display: 'inline-block', verticalAlign: 'middle' }} />
                                ) : (
                                    <Tooltip title={localeMessages["send_lesson_to_yourself"] || 'Send it to yourself'} placement="top">
                                        <span>
                                            <IconButton aria-label={localeMessages["send_lesson"] || 'Send lesson'} onClick={() => sendLessonToCurrentUser(content.id)}><ForwardToInboxOutlinedIcon /></IconButton>
                                        </span>
                                    </Tooltip>
                                )
                            )}
                        </TableCell>}
                    </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
        {(showQuizTwoAttemptNote || showQuizUnlimitedAttemptsNote) && (
            <Box
                sx={(theme) => ({
                    mt: 1.5,
                    px: 1.5,
                    py: 1,
                    display: { xs: 'none', md: 'flex' },
                    alignItems: 'flex-start',
                    gap: 1,
                    borderRadius: 1,
                    backgroundColor: theme.palette.mode === 'light' ? '#f5f5f7' : theme.palette.background.dark,
                })}
            >
                <InfoOutlinedIcon sx={{ fontSize: '0.95rem', mt: '1px', flexShrink: 0, color: 'text.disabled' }} />
                <Box>
                    {showQuizTwoAttemptNote && (
                        <Typography component="div" variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.75rem' }}>
                            <Box component="span" sx={{ fontWeight: 600 }}>{localeMessages["two_attempts"]}:</Box> {localeMessages["quiz_2_attempts_sub_note"]}
                        </Typography>
                    )}
                    {showQuizUnlimitedAttemptsNote && (
                        <Typography component="div" variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.75rem', mt: showQuizTwoAttemptNote ? 0.5 : 0 }}>
                            <Box component="span" sx={{ fontWeight: 600 }}>{localeMessages["unlimited_attempts"]}:</Box> {localeMessages["quiz_unlimited_attempts_sub_note"]}
                        </Typography>
                    )}
                </Box>
            </Box>
        )}
        </>
    );
}

export default ContentTable;
