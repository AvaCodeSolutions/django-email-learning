import { IconButton, Switch, TableContainer, Table, TableHead, TableRow, TableBody, TableCell, Paper, Typography, Tab } from '@mui/material';
import { useState, useEffect } from 'react';
import { getCookie } from '../../../src/utils.js';
import DeleteIcon from '@mui/icons-material/Delete';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { useAppContext } from '../../../src/render.jsx';


const ContentTable = ({ courseId, eventHandler, loaded = false }) => {
    const [contentList, setContentList] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [draggedContentId, setDraggedContentId] = useState(null);

    const startDrag = (contentId) => {
        setIsDragging(true);
        setDraggedContentId(contentId);
    }

    const { apiBaseUrl, userRole, localeMessages, direction } = useAppContext();
    const organizationId = localStorage.getItem('activeOrganizationId');

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
            loaded = true;
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

    return (
        <TableContainer component={Paper}>
           <Table sx={{ width: "100%" }} aria-label="Contents">
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
                {contentList.map((content) => (
                    <TableRow
                        key={content.id} {...(isDragging && draggedContentId === content.id && { sx: { backgroundColor: 'background.main', boxShadow: 2 } })}
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
                        onMouseDown={() => startDrag(content.id)}
                        /></TableCell>}
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}><Typography
                            onClick={() => {let event = {type: 'content_clicked', content_id: content.id}; eventHandler(event);}}
                            color='secondary.dark' sx={{ cursor: 'pointer'}}>{content.title}</Typography></TableCell>
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}>{formatPeriod(content.waiting_period)}</TableCell>
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}>{localeMessages[content.type]}</TableCell>
                        <TableCell align={direction == 'rtl' ? 'right' : 'left'}><Switch checked={content.is_published}  onChange={() => TogglePublishContent(content.id, !content.is_published)} disabled={userRole == 'viewer'} /></TableCell>
                        {userRole !== 'viewer' && <TableCell align={direction == 'rtl' ? 'right' : 'left'}>
                            <IconButton aria-label={localeMessages["delete"]} onClick={() => deleteContent(content.id)}>
                                <DeleteIcon />
                            </IconButton>
                        </TableCell>}
                    </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
    );
}

export default ContentTable;
