import { Alert, Box, CircularProgress, Chip, Divider, IconButton, ListItemIcon, ListItemText, Menu, MenuItem, Switch, TableContainer, Table, TableHead, TableRow, TableBody, TableCell, Paper, Tooltip, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import EmptyTableState from '../../../src/components/EmptyTableState.jsx';
import { useState, useEffect, useMemo, useRef } from 'react';
import DeleteIcon from '@mui/icons-material/Delete';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import BallotOutlinedIcon from '@mui/icons-material/BallotOutlined';
import AssignmentOutlinedIcon from '@mui/icons-material/AssignmentOutlined';
import LockClockOutlinedIcon from '@mui/icons-material/LockClockOutlined';
import CallSplitOutlinedIcon from '@mui/icons-material/CallSplitOutlined';
import AltRouteIcon from '@mui/icons-material/AltRoute';
import DriveFileMoveIcon from '@mui/icons-material/DriveFileMove';
import FlagIcon from '@mui/icons-material/Flag';
import SubdirectoryArrowRightIcon from '@mui/icons-material/SubdirectoryArrowRight';
import apiClient from '../../../src/apiClient.js';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ForwardToInboxOutlinedIcon from '@mui/icons-material/ForwardToInboxOutlined';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import MoreHorizIcon from '@mui/icons-material/MoreHoriz';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

import { useAppContext } from '../../../src/render.jsx';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';
import { buildContentTree, conditionLabel, trackColorMap } from './branching.js';

const TYPE_ICONS = { lesson: DescriptionOutlinedIcon, quiz: BallotOutlinedIcon, assignment: AssignmentOutlinedIcon, decision: CallSplitOutlinedIcon, gate: LockClockOutlinedIcon };
const TypeIcon = ({ type, ...props }) => {
    const Icon = TYPE_ICONS[type] || AssignmentOutlinedIcon;
    return <Icon {...props} />;
};

const trackOf = (content) => content.track_id ?? null;

// The drag handle column's full width, padding included, per breakpoint.
const DRAG_COLUMN_WIDTH = { xs: 56, sm: 40 };
// A row's indent at each depth, in theme spacing units.
const INDENT = { xs: { base: 0.5, step: 1.5 }, sm: { base: 2, step: 3 } };
const SPACING_PX = 8;

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
    const [actionsMenu, setActionsMenu] = useState(null);
    // A drag that ends over its own row would otherwise also count as a click on it.
    const suppressRowClickRef = useRef(false);

    const { apiBaseUrl: rawApiBaseUrl, userRole, localeMessages, direction } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');
    const canSendLesson = userRole === 'admin' || userRole === 'editor';
    const canEditBranching = userRole === 'admin' || userRole === 'editor';
    const canMove = canEditBranching && tracks.length > 0;
    const canAuthor = userRole !== 'viewer';
    const columnCount = canAuthor ? 5 : 3;
    const alignStart = direction == 'rtl' ? 'right' : 'left';
    const branchPointIds = useMemo(() => new Set(transitions.map((rule) => rule.source_id)), [transitions]);
    const rows = useMemo(() => buildContentTree(contentList, tracks, transitions), [contentList, tracks, transitions]);
    // A branch point routes on the first submission, so the attempt notes do not describe it.
    const showQuizTwoAttemptNote = contentList.some((content) => content.type === 'quiz' && !branchPointIds.has(content.id) && content.is_blocking !== false && content.limited_attempts == true);
    const showQuizUnlimitedAttemptsNote = contentList.some((content) => content.type === 'quiz' && !branchPointIds.has(content.id) && content.is_blocking !== false && content.limited_attempts == false);
    const trackColors = useMemo(() => trackColorMap(tracks), [tracks]);
    const indent = (depth) => ({ xs: INDENT.xs.base + depth * INDENT.xs.step, sm: INDENT.sm.base + depth * INDENT.sm.step });
    // Branch and rejoin rows are one cell across the whole row, so for authors they also skip the
    // drag column: that lines their icon up with the type icons of the contents below.
    const fullRowIndent = (depth) => {
        if (!canAuthor) {
            return indent(depth);
        }
        const px = (breakpoint) => `${DRAG_COLUMN_WIDTH[breakpoint] + (INDENT[breakpoint].base + depth * INDENT[breakpoint].step) * SPACING_PX}px`;
        return { xs: px('xs'), sm: px('sm') };
    };
    // A track's rows share its colour with the course map; contents on a track the listing
    // did not return fall back to the primary colour.
    const trackColor = (trackId) => (theme) => trackColors.get(trackId) ?? theme.palette.primary.main;
    const trackBorder = (trackId) => (theme) => `3px solid ${trackColor(trackId)(theme)}`;
    // Once a course has tracks, the main path gets a neutral lane of its own, as it does in the
    // course map, so a track reads as branching off it. Without tracks there is nothing to tell apart.
    const contentBorder = (content, depth) => {
        if (depth > 0) {
            return trackBorder(content.track_id);
        }
        return tracks.length > 0 ? (theme) => `3px solid ${theme.palette.divider}` : undefined;
    };
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
            if (dragId !== null) {
                suppressRowClickRef.current = true;
                window.setTimeout(() => { suppressRowClickRef.current = false; }, 0);
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
                eventHandler({ type: 'content_published', content_id: contentId, is_published: is_published });
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

    const openContent = (contentId) => {
        eventHandler({ type: 'content_clicked', content_id: contentId });
    }

    // Controls inside a row handle their own clicks; this keeps them from also opening the content.
    const stopRowClick = (event) => event.stopPropagation();

    const actionsLabel = localeMessages["more_actions"] || 'More actions';

    const actionsButton = (content) => (
        sendingContentId === content.id ? (
            <CircularProgress size="18px" sx={{ display: 'inline-block', verticalAlign: 'middle', m: '7px' }} />
        ) : (
            <IconButton
                size="small"
                aria-label={`${actionsLabel}: ${content.title}`}
                aria-haspopup="menu"
                onClick={(event) => { event.stopPropagation(); setActionsMenu({ anchorEl: event.currentTarget, content }); }}
            >
                <MoreHorizIcon fontSize="small" />
            </IconButton>
        )
    );

    const publishSwitch = (content) => (
        <Switch
            size="small"
            checked={content.is_published}
            onClick={stopRowClick}
            onChange={() => TogglePublishContent(content.id, !content.is_published)}
            disabled={!canAuthor}
            slotProps={{ input: { 'aria-label': `${localeMessages["published"] || 'Published'}: ${content.title}` } }}
        />
    );

    // The short facts about a content, as one muted line under its title.
    const contentDetails = (content, isBranchPoint) => {
        const details = [];
        if (content.type === 'quiz' && content.is_blocking === false) {
            details.push(<span key="practice">{localeMessages["practice_quiz"]}</span>);
        }
        if (content.type === 'gate' && content.gate_key) {
            details.push(<Box key="gate-key" component="span" sx={{ fontFamily: 'monospace' }}>{content.gate_key}</Box>);
        }
        if (isBranchPoint) {
            details.push(
                <Box key="branching" component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25, color: 'primary.main' }}>
                    <AltRouteIcon sx={{ fontSize: '0.85rem' }} />
                    {localeMessages["quiz_tab_branching"] || 'Branching'}
                </Box>
            );
        } else if (content.type === 'quiz' && content.is_blocking !== false && content.limited_attempts !== null && content.limited_attempts !== undefined) {
            details.push(<span key="attempts">{content.limited_attempts ? localeMessages["two_attempts"] : localeMessages["unlimited_attempts"]}</span>);
        }
        if (details.length === 0) {
            return null;
        }
        return (
            <Typography component="div" variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', columnGap: 0.75, lineHeight: 1.4 }}>
                {details.flatMap((detail, index) => (index === 0 ? [detail] : [<span key={`sep-${index}`} aria-hidden="true">·</span>, detail]))}
            </Typography>
        );
    };

    const renderContentRow = ({ key, content, depth, isBranchPoint }) => {
        const isDragged = isDragging && draggedContentId === content.id;
        const typeLabel = localeMessages[content.type] || content.type;
        // The lane border goes on the row's first cell, so it lines up with the full-width branch
        // and rejoin rows: the drag handle for authors, the title for viewers.
        const laneBorder = contentBorder(content, depth);
        return (
        <TableRow
            key={key}
            data-content-id={content.id}
            hover={!isDragging}
            onClick={() => {
                if (!suppressRowClickRef.current) {
                    openContent(content.id);
                }
            }}
            sx={{
                cursor: isDragging ? 'grabbing' : 'pointer',
                transition: 'transform 120ms ease, box-shadow 120ms ease, background-color 120ms ease',
                '&:hover .drag-handle': { opacity: 1 },
                ...(isDragged
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
            {canAuthor && (
                <TableCell
                    align={alignStart}
                    onClick={stopRowClick}
                    sx={{ cursor: 'grab', boxSizing: 'border-box', width: { xs: `${DRAG_COLUMN_WIDTH.xs}px`, sm: `${DRAG_COLUMN_WIDTH.sm}px` }, minWidth: { xs: `${DRAG_COLUMN_WIDTH.xs}px`, sm: `${DRAG_COLUMN_WIDTH.sm}px` }, padding: { xs: '8px 4px', sm: '8px 0' }, textAlign: 'center', borderInlineStart: laneBorder }}
                >
                    <DragIndicatorIcon
                        className="drag-handle"
                        fontSize="small"
                        onMouseDown={(event) => startDrag(event, content.id)}
                        onTouchStart={(event) => startDrag(event, content.id)}
                        // Shown on row hover from sm up; always on touch screens, which cannot hover.
                        sx={{ color: 'text.secondary', opacity: { xs: 1, sm: isDragged ? 1 : 0 }, transition: 'opacity 0.15s', '@media (hover: none)': { opacity: 1 } }}
                    />
                </TableCell>
            )}
            <TableCell align={alignStart} sx={{ position: 'relative', paddingInlineStart: indent(depth), borderInlineStart: canAuthor ? undefined : laneBorder }}>
                {isDragged && (
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
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                    <Tooltip title={typeLabel} placement="top">
                        <Box component="span" sx={{ display: 'inline-flex', color: 'text.secondary', mt: '2px' }}>
                            <TypeIcon type={content.type} fontSize="small" titleAccess={typeLabel} />
                        </Box>
                    </Tooltip>
                    <Box sx={{ minWidth: 0 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', columnGap: 1 }}>
                            <Box
                                component="span"
                                role="button"
                                tabIndex={0}
                                onKeyDown={(event) => {
                                    if (event.key === 'Enter' || event.key === ' ') {
                                        event.preventDefault();
                                        openContent(content.id);
                                    }
                                }}
                                sx={{ fontWeight: 500, color: content.is_published ? 'text.primary' : 'text.secondary', '&:focus-visible': { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: 2, borderRadius: 0.5 } }}
                            >
                                {content.title}
                            </Box>
                            {!content.is_published && (
                                <Box component="span" sx={{ fontSize: '0.7rem', lineHeight: 1.6, px: 0.75, borderRadius: 1, border: '1px solid', borderColor: 'divider', color: 'text.secondary' }}>
                                    {localeMessages["not_published"] || 'Not published'}
                                </Box>
                            )}
                        </Box>
                        {contentDetails(content, isBranchPoint)}
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
                        {publishSwitch(content)}
                    </Box>
                    {canAuthor && <>
                        <Box sx={{ width: '1px', height: '14px', backgroundColor: 'divider' }} />
                        <Box sx={{ display: 'flex', alignItems: 'center', px: 0.5 }}>
                            {actionsButton(content)}
                        </Box>
                    </>}
                </Box>
            </TableCell>
            <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, color: 'text.secondary' }} align={alignStart}>{formatPeriod(content.waiting_period)}</TableCell>
            <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }} align={alignStart}>{publishSwitch(content)}</TableCell>
            {canAuthor && <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, width: 56 }} align="center">
                {actionsButton(content)}
            </TableCell>}
        </TableRow>
        );
    };

    const renderBranchRow = ({ key, track, rules, alsoFrom, depth }) => {
        const editLabel = localeMessages["edit_track"] || 'Edit Track';
        const deleteLabel = localeMessages["delete_track"] || 'Delete Track';
        return (
            <TableRow key={key} data-track-id={track.id} sx={{ backgroundColor: (theme) => alpha(trackColor(track.id)(theme), theme.palette.mode === 'dark' ? 0.16 : 0.07) }}>
                <TableCell colSpan={columnCount} sx={{ py: 0.75, paddingInlineStart: fullRowIndent(depth), borderInlineStart: trackBorder(track.id) }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                        <AltRouteIcon fontSize="small" sx={{ color: trackColor(track.id) }} />
                        {rules.map((rule) => (
                            <Chip key={rule.id} size="small" variant="outlined" label={conditionLabel(rule, localeMessages)} sx={{ color: trackColor(track.id), borderColor: trackColor(track.id) }} />
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

    const renderRejoinRow = ({ key, track, mergeContent, depth }) => (
        <TableRow key={key}>
            <TableCell colSpan={columnCount} sx={{ py: 0.5, paddingInlineStart: fullRowIndent(depth), borderInlineStart: trackBorder(track.id) }}>
                {/* In the track's colour, like its header, so the line reads as closing that track. */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, color: trackColor(track.id) }}>
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
                {canAuthor && <TableCell sx={{ width: `${DRAG_COLUMN_WIDTH.sm}px`, boxSizing: 'border-box' }}></TableCell>}
                <TableCell sx={{ textAlign: alignStart }}>{localeMessages["title"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: alignStart, width: 140 }}>{localeMessages["waiting_time"]}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, textAlign: alignStart, width: 110 }}>{localeMessages["published"]}</TableCell>
                {canAuthor && <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' }, width: 56 }} align="center">{localeMessages["actions"]}</TableCell>}
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
        {/* Rendered once outside the rows: React bubbles a portal's clicks through the tree it was
            declared in, so a menu inside a row would also open that row's content. */}
        <Menu
            anchorEl={actionsMenu?.anchorEl}
            open={Boolean(actionsMenu)}
            onClose={() => setActionsMenu(null)}
            anchorOrigin={{ vertical: 'bottom', horizontal: direction === 'rtl' ? 'left' : 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: direction === 'rtl' ? 'left' : 'right' }}
        >
            {actionsMenu && [
                <MenuItem key="edit" onClick={() => { const { content } = actionsMenu; setActionsMenu(null); openContent(content.id); }}>
                    <ListItemIcon><EditOutlinedIcon fontSize="small" /></ListItemIcon>
                    <ListItemText>{localeMessages["edit"] || 'Edit'}</ListItemText>
                </MenuItem>,
                canMove && (
                    <MenuItem key="move" onClick={() => { const { anchorEl, content } = actionsMenu; setActionsMenu(null); setMoveMenu({ anchorEl, content }); }}>
                        <ListItemIcon><DriveFileMoveIcon fontSize="small" /></ListItemIcon>
                        <ListItemText>{moveLabel}</ListItemText>
                    </MenuItem>
                ),
                canSendLesson && actionsMenu.content.type === 'lesson' && (
                    <MenuItem key="send" onClick={() => { const { content } = actionsMenu; setActionsMenu(null); sendLessonToCurrentUser(content.id); }}>
                        <ListItemIcon><ForwardToInboxOutlinedIcon fontSize="small" /></ListItemIcon>
                        <ListItemText>{localeMessages["send_lesson_to_yourself"] || 'Send it to yourself'}</ListItemText>
                    </MenuItem>
                ),
                <Divider key="divider" />,
                <MenuItem key="delete" onClick={() => { const { content } = actionsMenu; setActionsMenu(null); deleteContent(content.id); }} sx={{ color: 'error.main' }}>
                    <ListItemIcon sx={{ color: 'inherit' }}><DeleteIcon fontSize="small" /></ListItemIcon>
                    <ListItemText>{localeMessages["delete"]}</ListItemText>
                </MenuItem>,
            ].filter(Boolean)}
        </Menu>
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
