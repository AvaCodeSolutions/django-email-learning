import { IconButton, Switch, TableContainer, Table, TableHead, TableRow, TableBody, TableCell, Paper, Typography, Tab } from '@mui/material';
import { useState, useEffect } from 'react';
import { getCookie } from '../../src/utils.js';
import DeleteIcon from '@mui/icons-material/Delete';

const ContentTable = ({ courseId, eventHandler, loaded = false }) => {
    const [contentList, setContentList] = useState([]);

    const apiBaseUrl = localStorage.getItem('apiBaseUrl');
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
        getContets();
    }, [loaded]);

    const deleteContent = (contentId) => {
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
        })
            .then(response => {
                if (response.ok) {
                    setContentList(contentList.filter(content => content.id !== contentId));
                } else {
                    console.error('Error deleting content:', response.statusText);
                }
            })
            .catch(error => console.error('Error deleting content:', error));
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
                <TableCell>Title</TableCell>
                <TableCell>Waiting time</TableCell>
                <TableCell>type</TableCell>
                <TableCell>Published</TableCell>
                <TableCell align='right'>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
                {contentList.map((content) => (
                    <TableRow key={content.id}>
                        <TableCell><Typography
                            onClick={() => {let event = {type: 'content_clicked', content_id: content.id}; eventHandler(event);}}
                            color='primary.dark' sx={{ cursor: 'pointer'}}>{content.title}</Typography></TableCell>
                        <TableCell>{formatPeriod(content.waiting_period)}</TableCell>
                        <TableCell>{content.type}</TableCell>
                        <TableCell><Switch defaultChecked={content.is_published} onChange={() => TogglePublishContent(content.id, !content.is_published)} /></TableCell>
                        <TableCell align='right'>
                            <IconButton aria-label="delete" onClick={() => deleteContent(content.id)}>
                                <DeleteIcon />
                            </IconButton>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
    );
}

export default ContentTable;
