import { Alert, Box, CircularProgress, Chip, IconButton, Switch, TableContainer, Table, TableHead, TableRow, TableBody, TableCell, Paper, Tooltip, Typography } from '@mui/material';
import EmptyTableState from '../../../src/components/EmptyTableState.jsx';
import { useState, useEffect } from 'react';
import { getCookie } from '../../../src/utils.js';
import DeleteIcon from '@mui/icons-material/Delete';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ForwardToInboxOutlinedIcon from '@mui/icons-material/ForwardToInboxOutlined';

import { useAppContext } from '../../../src/render.jsx';


const ContentTable = ({ courseId, eventHandler, loaded = false }) => {
    const [contentList, setContentList] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [draggedContentId, setDraggedContentId] = useState(null);
    const [sendingContentId, setSendingContentId] = useState(null);
    const [sendSuccessMessage, setSendSuccessMessage] = useState('');

    const startDrag = (event, contentId) => {
        event.preventDefault();
        setIsDragging(true);
        setDraggedContentId(contentId);
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
        const onPointerUp = () => {
            console.log('Pointer released anywhere');
            setIsDragging(false);
            setDraggedContentId(null);
        };

        window.addEventListener('pointerup', onPointerUp);

        return () => window.removeEventListener('pointerup', onPointerUp);
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
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                is_published: is_published
            })
        })
            .then(response => {
                if (response.ok) {
                    console.log('Publish status toggled successfully');
                    // Update the local state to reflect the change
                    setContentList(contentList.map(content => {
                        if (content.id === contentId) {
                            return { ...content, is_published: !content.is_published };
                        }
                        return content;
                    }));
                } else {
                    console.error('Error toggling publish status:', response.statusText);
                }
            })
            .catch(error => console.error('Error toggling publish status:', error));
    }


    const getContets = () => {

        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
        })
            .then(response => response.json())
            .then(data => {
                setContentList(data.course_contents);
                let event = {type: 'content_loaded', data: data};
                eventHandler(event);
            })
            .catch(error => console.error('Error fetching content list:', error));
    }

    const sendLessonToCurrentUser = (contentId) => {
        setSendingContentId(contentId);
        fetch(`${apiBaseUrl}/organizations/${organizationId}/send-lesson/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                id: contentId,
            }),
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Send lesson failed with status ${response.status}`);
                }
                return response.json();
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
          <TableContainer component={Paper} dir={direction}>
              <Table sx={{ width: "100%", direction: direction }} aria-label="Contents">
            <TableHead>
              <TableRow>
                { userRole !== 'viewer' && <TableCell sx={{ width: '40px', boxSizing: 'border-box' }}></TableCell>}
                <TableCell sx={{ textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["title"]}</TableCell>
                <TableCell sx={{ textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["waiting_time"]}</TableCell>
                <TableCell sx={{ textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["type"]}</TableCell>
                <TableCell sx={{ textAlign: direction == 'rtl' ? 'right' : 'left' }}>{localeMessages["published"]}</TableCell>
                {userRole !== 'viewer' && <TableCell align={direction == 'rtl' ? 'right' : 'left'}>{localeMessages["actions"]}</TableCell>}
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
                         { userRole !== 'viewer' && <TableCell align={direction == 'rtl' ? 'right' : 'left'} sx={{ cursor: 'grab', width: '40px', padding: '8px 0', textAlign: 'center' }}><DragIndicatorIcon fontSize="small"
                        onMouseDown={(event) => startDrag(event, content.id)}
                        /></TableCell>}
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}><Typography
                            component="span"
                            onClick={() => {let event = {type: 'content_clicked', content_id: content.id}; eventHandler(event);}}
                            sx={{ cursor: 'pointer', color: theme => theme.palette.mode === 'dark' ? theme.palette.secondary.main : theme.palette.secondary.dark }}>{content.title}
                            {content.type === 'quiz' && content.is_blocking === false && (
                                <Chip
                                    label={localeMessages["practice_quiz"]}
                                    size="small"
                                    sx={(theme) => ({
                                        ml: 1,
                                        backgroundColor: theme.palette.mode === 'dark' ? 'rgba(33, 150, 243, 0.2)' : 'rgba(33, 150, 243, 0.14)',
                                        color: theme.palette.mode === 'dark' ? '#64B5F6' : '#0D47A1',
                                    })}
                                />
                            )}
                            {content.type === 'quiz' && content.is_blocking !== false && content.limited_attempts !== null &&  ( content.limited_attempts ? <Chip label={localeMessages["two_attempts"]} size="small" sx={(theme) => ({ ml: 1, backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255, 152, 0, 0.15)' : 'rgba(255, 203, 71, 0.5)', color: theme.palette.mode === 'dark' ? '#FF9800' : '#9a4208' })}
                             /> : <Chip label={localeMessages["unlimited_attempts"]} size="small" sx={(theme) => ({ ml: 1, backgroundColor: theme.palette.mode === 'dark' ? 'rgba(76, 175, 80, 0.15)' : 'rgba(129, 199, 132, 0.5)', color: theme.palette.mode === 'dark' ? '#4CAF50' : '#256029' })} />)}</Typography></TableCell>
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}>{formatPeriod(content.waiting_period)}</TableCell>
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}>{localeMessages[content.type]}</TableCell>
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}><Switch checked={content.is_published}  onChange={() => TogglePublishContent(content.id, !content.is_published)} disabled={userRole == 'viewer'} /></TableCell>
                        {userRole !== 'viewer' && <TableCell align={direction == 'rtl' ? 'right' : 'left'}>

                            <IconButton aria-label={localeMessages["delete"]} onClick={() => deleteContent(content.id)}>
                                <DeleteIcon />
                            </IconButton>
                            {canSendLesson && content.type === 'lesson' && (
                                sendingContentId === content.id ? (
                                    <CircularProgress size="18px" sx={{ display: 'inline-block', verticalAlign: 'middle' }} />
                                ) : (
                                    <Tooltip title={localeMessages["send_lesson_to_yourself"] || 'Send it to yourself'} placement="top">
                                        <span>
                                            <IconButton
                                                aria-label={localeMessages["send_lesson"] || 'Send lesson'}
                                                onClick={() => sendLessonToCurrentUser(content.id)}
                                            >
                                                <ForwardToInboxOutlinedIcon />
                                            </IconButton>
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
                sx={{
                    mt: 1.5,
                    px: 1.5,
                    py: 1,
                    borderRadius: 1,
                    backgroundColor: 'action.hover',
                    border: '1px solid',
                    borderColor: 'divider',
                }}
            >
                {showQuizTwoAttemptNote && (
                    <Typography component="div" variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        • <Box component="span" sx={{ fontWeight: 600 }}>{localeMessages["two_attempts"]}:</Box> {localeMessages["quiz_2_attempts_sub_note"]}
                    </Typography>
                )}
                {showQuizUnlimitedAttemptsNote && (
                    <Typography component="div" variant="caption" color="text.secondary" sx={{ display: 'block', mt: showQuizTwoAttemptNote ? 0.5 : 0 }}>
                        • <Box component="span" sx={{ fontWeight: 600 }}>{localeMessages["unlimited_attempts"]}:</Box> {localeMessages["quiz_unlimited_attempts_sub_note"]}
                    </Typography>
                )}
            </Box>
        )}
        </>
    );
}

export default ContentTable;
