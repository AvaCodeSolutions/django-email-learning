import { Alert, Box, CircularProgress, Chip, IconButton, Menu, MenuItem, Switch, TableContainer, Table, TableHead, TableRow, TableBody, TableCell, Paper, Tooltip, Typography } from '@mui/material';
import EmptyTableState from '../../../src/components/EmptyTableState.jsx';
import { useState, useEffect, useMemo, useRef } from 'react';
import DeleteIcon from '@mui/icons-material/Delete';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import BallotOutlinedIcon from '@mui/icons-material/BallotOutlined';
import AssignmentOutlinedIcon from '@mui/icons-material/AssignmentOutlined';
import AltRouteIcon from '@mui/icons-material/AltRoute';
import DriveFileMoveIcon from '@mui/icons-material/DriveFileMove';
import FlagIcon from '@mui/icons-material/Flag';
import SubdirectoryArrowRightIcon from '@mui/icons-material/SubdirectoryArrowRight';
import apiClient from '../../../src/apiClient.js';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ForwardToInboxOutlinedIcon from '@mui/icons-material/ForwardToInboxOutlined';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

import { useAppContext } from '../../../src/render.jsx';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';
import { buildContentTree, conditionLabel } from './branching.js';

const trackOf = (content) => content.track_id ?? null;

const idsOnTrack = (list, trackId) => list.filter((content) => trackOf(content) === trackId).map((content) => content.id);

// Priorities are ordered within a track, so a row only ever changes places with a row on its own track.
const moveWithinTrack = (list, dragId, hoverId) => {
    const draggedIndex = list.findIndex((content) => content.id === dragId);
    const hoverIndex = list.findIndex((content) => content.id === hoverId);
    if (draggedIndex === -1 || hoverIndex === -1 || trackOf(list[draggedIndex]) !== trackOf(list[hoverIndex])) {
        return null;
    }
    const newList = [...list];
    const [draggedItem] = newList.splice(draggedIndex, 1);
    newList.splice(hoverIndex, 0, draggedItem);
    return newList;
};

const ContentTable = ({ courseId, eventHandler, loaded = false }) => {
    const [contentList, setContentList] = useState([]);
    const [tracks, setTracks] = useState([]);
    const [transitions, setTransitions] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [draggedContentId, setDraggedContentId] = useState(null);
    const contentListRef = useRef(contentList);
    const draggedContentIdRef = useRef(draggedContentId);
    const dragStartOrderRef = useRef(null);
    const eventHandlerRef = useRef(eventHandler);
    const [sendingContentId, setSendingContentId] = useState(null);
    const [sendSuccessMessage, setSendSuccessMessage] = useState('');
    const [moveMenu, setMoveMenu] = useState(null);

    const { apiBaseUrl: rawApiBaseUrl, userRole, localeMessages, direction } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');
    const canSendLesson = userRole === 'admin' || userRole === 'editor';
    const canEditBranching = userRole === 'admin' || userRole === 'editor';
    const canMove = canEditBranching && tracks.length > 0;
    const columnCount = userRole !== 'viewer' ? 6 : 5;
    const alignStart = direction == 'rtl' ? 'right' : 'left';
    const branchPointIds = useMemo(() => new Set(transitions.map((rule) => rule.source_id)), [transitions]);
    const rows = useMemo(() => buildContentTree(contentList, tracks, transitions), [contentList, tracks, transitions]);
    // A branch point routes on the first submission, so the attempt notes do not describe it.
    const showQuizTwoAttemptNote = contentList.some((content) => content.type === 'quiz' && !branchPointIds.has(content.id) && content.is_blocking !== false && content.limited_attempts == true);
    const showQuizUnlimitedAttemptsNote = contentList.some((content) => content.type === 'quiz' && !branchPointIds.has(content.id) && content.is_blocking !== false && content.limited_attempts == false);
    const indent = (depth) => ({ xs: 0.5 + depth * 1.5, sm: 2 + depth * 3 });
    const trackAccent = (depth) => (depth > 0 ? (theme) => `3px solid ${theme.palette.primary.light}` : undefined);
    const moveLabel = localeMessages["move_to_track"] || 'Move to';

    const startDrag = (event, contentId) => {
        event.preventDefault();
        const dragged = contentListRef.current.find((content) => content.id === contentId);
        dragStartOrderRef.current = dragged ? idsOnTrack(contentListRef.current, trackOf(dragged)) : null;
        setIsDragging(true);
        setDraggedContentId(contentId);
        draggedContentIdRef.current = contentId;
    }

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
        eventHandlerRef.current = eventHandler;
    }, [eventHandler]);

    useEffect(() => {
        if (!loaded) {
            getContents();
        }
    }, [loaded]);

    useEffect(() => {
        contentListRef.current = contentList;
    }, [contentList]);

    useEffect(() => {
        const onPointerUp = () => {
            const dragId = draggedContentIdRef.current;
            const startOrder = dragStartOrderRef.current;
            if (dragId !== null && startOrder) {
                const dragged = contentListRef.current.find((content) => content.id === dragId);
                const endOrder = dragged ? idsOnTrack(contentListRef.current, trackOf(dragged)) : startOrder;
                // Sent once, on drop: a position passed through mid-drag can be one the server
                // refuses, such as a merge point momentarily ahead of its branch point.
                if (endOrder.join(',') !== startOrder.join(',')) {
                    eventHandlerRef.current({ type: 'content_reordered', new_order: endOrder });
                }
            }
            dragStartOrderRef.current = null;
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
            const list = contentListRef.current;
            const hovered = list.find((content) => String(content.id) === row.dataset.contentId);
            if (!hovered || hovered.id === draggedContentIdRef.current) return;
            const newList = moveWithinTrack(list, draggedContentIdRef.current, hovered.id);
            if (!newList) return;
            contentListRef.current = newList;
            setContentList(newList);
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

    const getContents = () => {
        apiClient.get(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents`)
            .then(data => {
                setContentList(data.course_contents);
                setTracks(data.tracks || []);
                setTransitions(data.transitions || []);
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

    const moveTo = (trackId) => {
        const content = moveMenu?.content;
        setMoveMenu(null);
        if (!content || trackOf(content) === trackId) {
            return;
        }
        eventHandler({ type: 'content_moved', content_id: content.id, track_id: trackId });
    }

    const moveButton = (content, size) => (
        <Tooltip title={moveLabel} placement="top">
            <IconButton size={size} aria-label={`${moveLabel}: ${content.title}`} onClick={(event) => setMoveMenu({ anchorEl: event.currentTarget, content })}>
                <DriveFileMoveIcon fontSize={size === 'small' ? 'small' : undefined} />
            </IconButton>
        </Tooltip>
    );

    const renderContentRow = ({ key, content, depth, isBranchPoint }) => (
        <TableRow
            key={key}
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
                    const newContentList = moveWithinTrack(contentList, draggedContentId, content.id);
                    if (newContentList) {
                        setContentList(newContentList);
                    }
                }
            }}>
             { userRole !== 'viewer' && <TableCell align={alignStart} sx={{ cursor: 'grab', width: { xs: '48px', sm: '40px' }, minWidth: { xs: '48px', sm: '40px' }, padding: { xs: '8px 4px', sm: '8px 0' }, textAlign: 'center' }}><DragIndicatorIcon fontSize="small"
            onMouseDown={(event) => startDrag(event, content.id)}
            onTouchStart={(event) => startDrag(event, content.id)}
            /></TableCell>}
            <TableCell align={alignStart} sx={{ position: 'relative', paddingInlineStart: indent(depth), borderInlineStart: trackAccent(depth) }}>
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
                        {userRole !== 'viewer' && <EditOutlinedIcon className="edit-icon" sx={{ fontSize: '0.9rem', opacity: 1, transition: 'opacity 0.15s', verticalAlign: 'middle', ml: 1 }} />}
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
                        <Switch size="small" checked={content.is_published} onChange={() => TogglePublishContent(content.id, !content.is_published)} disabled={userRole == 'viewer'} slotProps={{ input: { 'aria-label': `${localeMessages["published"] || 'Published'}: ${content.title}` } }} />
                    </Box>
                    {userRole !== 'viewer' && <>
                        <Box sx={{ width: '1px', height: '14px', backgroundColor: 'divider' }} />
                        <Box sx={{ display: 'flex', alignItems: 'center', px: 0.5 }}>
                            <IconButton size="small" aria-label={localeMessages["delete"]} onClick={() => deleteContent(content.id)}><DeleteIcon fontSize="small" /></IconButton>
                            {canMove && moveButton(content, 'small')}
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
            <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={alignStart}>{formatPeriod(content.waiting_period)}</TableCell>
            <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={alignStart}>
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.5 }}>
                    <Chip
                        size="small"
                        icon={content.type === 'lesson' ? <DescriptionOutlinedIcon /> : content.type === 'quiz' ? <BallotOutlinedIcon /> : <AssignmentOutlinedIcon />}
                        label={localeMessages[content.type]}
                        variant="outlined"
                        sx={(theme) => ({ fontSize: '0.75rem', color: theme.palette.mode === 'dark' ? theme.palette.text.primary : undefined, borderColor: theme.palette.mode === 'dark' ? theme.palette.text.secondary : undefined })}
                    />
                    {isBranchPoint ? (
                        <Chip
                            size="small"
                            icon={<AltRouteIcon />}
                            label={localeMessages["quiz_tab_branching"] || 'Branching'}
                            color="primary"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                        />
                    ) : content.type === 'quiz' && content.is_blocking !== false && content.limited_attempts !== null && (
                        <Chip
                            size="small"
                            variant="outlined"
                            label={content.limited_attempts ? localeMessages["two_attempts"] : localeMessages["unlimited_attempts"]}
                            sx={{ fontSize: '0.7rem', color: 'text.secondary', borderColor: 'divider' }}
                        />
                    )}
                </Box>
            </TableCell>
            <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={alignStart}><Switch checked={content.is_published} onChange={() => TogglePublishContent(content.id, !content.is_published)} disabled={userRole == 'viewer'} slotProps={{ input: { 'aria-label': `${localeMessages["published"] || 'Published'}: ${content.title}` } }} /></TableCell>
            {userRole !== 'viewer' && <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={alignStart}>
                <IconButton aria-label={localeMessages["delete"]} onClick={() => deleteContent(content.id)}><DeleteIcon /></IconButton>
                {canMove && moveButton(content, 'medium')}
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
    );

    const renderBranchRow = ({ key, track, rules, alsoFrom, depth }) => {
        const editLabel = localeMessages["edit_track"] || 'Edit Track';
        const deleteLabel = localeMessages["delete_track"] || 'Delete Track';
        return (
            <TableRow key={key} data-track-id={track.id} sx={{ backgroundColor: 'action.hover' }}>
                <TableCell colSpan={columnCount} sx={{ py: 0.75, paddingInlineStart: indent(depth), borderInlineStart: (theme) => `3px solid ${theme.palette.primary.main}` }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                        <AltRouteIcon fontSize="small" sx={{ color: 'primary.main' }} />
                        {rules.map((rule) => (
                            <Chip key={rule.id} size="small" color="primary" variant="outlined" label={conditionLabel(rule, localeMessages)} />
                        ))}
                        <Typography component="span" variant="body2" sx={{ fontWeight: 600 }}>{track.name}</Typography>
                        {alsoFrom.length > 0 && (
                            <Typography component="span" variant="caption" color="text.secondary">
                                {(localeMessages["also_reached_from"] || 'Also reached from: SOURCES').replace('SOURCES', alsoFrom.map((content) => content.title).join(', '))}
                            </Typography>
                        )}
                        {canEditBranching && (
                            <Box sx={{ marginInlineStart: 'auto', display: 'flex' }}>
                                <Tooltip title={editLabel}>
                                    <IconButton size="small" aria-label={`${editLabel}: ${track.name}`} onClick={() => eventHandler({ type: 'edit_track', track })}>
                                        <EditOutlinedIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                                <Tooltip title={deleteLabel}>
                                    <IconButton size="small" aria-label={`${deleteLabel}: ${track.name}`} onClick={() => eventHandler({ type: 'delete_track', track })}>
                                        <DeleteIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                            </Box>
                        )}
                    </Box>
                </TableCell>
            </TableRow>
        );
    };

    const renderRejoinRow = ({ key, mergeContent, depth }) => (
        <TableRow key={key}>
            <TableCell colSpan={columnCount} sx={{ py: 0.5, paddingInlineStart: indent(depth), borderInlineStart: (theme) => `3px solid ${theme.palette.primary.main}` }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, color: 'text.secondary' }}>
                    {mergeContent ? <SubdirectoryArrowRightIcon fontSize="small" /> : <FlagIcon fontSize="small" />}
                    <Typography variant="caption">
                        {mergeContent
                            ? (localeMessages["rejoins_at"] || 'Rejoins at TITLE').replace('TITLE', mergeContent.title)
                            : (localeMessages["ends_the_course"] || 'Ends the course')}
                    </Typography>
                </Box>
            </TableCell>
        </TableRow>
    );

    const renderUnroutedRow = ({ key }) => (
        <TableRow key={key}>
            <TableCell colSpan={columnCount} sx={{ pt: 2, pb: 0.5 }}>
                <Typography variant="overline" color="text.secondary">
                    {localeMessages["unrouted_tracks"] || 'Tracks no rule routes onto yet'}
                </Typography>
            </TableCell>
        </TableRow>
    );

    const renderRow = (row) => {
        if (row.kind === 'content') return renderContentRow(row);
        if (row.kind === 'branch') return renderBranchRow(row);
        if (row.kind === 'rejoin') return renderRejoinRow(row);
        return renderUnroutedRow(row);
    };

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
                <TableCell sx={{ textAlign: alignStart }}>{localeMessages["title"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: alignStart }}>{localeMessages["waiting_time"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: alignStart }}>{localeMessages["type"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: alignStart }}>{localeMessages["published"]}</TableCell>
                {userRole !== 'viewer' && <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={alignStart}>{localeMessages["actions"]}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
                {contentList.length === 0 && tracks.length === 0 && (
                  <EmptyTableState
                    colSpan={columnCount}
                    message={localeMessages['no_content_found'] || 'No content added yet.'}
                  />
                )}
                {rows.map(renderRow)}
            </TableBody>
          </Table>
        </TableContainer>
        <Menu anchorEl={moveMenu?.anchorEl} open={Boolean(moveMenu)} onClose={() => setMoveMenu(null)}>
            <MenuItem disabled={moveMenu ? trackOf(moveMenu.content) === null : false} onClick={() => moveTo(null)}>
                {localeMessages["main_path"] || 'Main path'}
            </MenuItem>
            {tracks.map((track) => (
                <MenuItem key={track.id} disabled={moveMenu ? trackOf(moveMenu.content) === track.id : false} onClick={() => moveTo(track.id)}>
                    {track.name}
                </MenuItem>
            ))}
        </Menu>
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
