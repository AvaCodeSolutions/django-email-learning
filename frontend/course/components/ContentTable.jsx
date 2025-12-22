import { TableContainer, Table, TableHead, TableRow, TableBody, TableCell, Paper, Typography } from '@mui/material';
import { useState, useEffect } from 'react';
import { getCookie } from '../../src/utils.js';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';

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
                        <TableCell align='right'>
                            <DeleteOutlineIcon sx={{ cursor: 'pointer', color: 'secondary.main' }} onClick={() => deleteContent(content.id)} />
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
    );
}

export default ContentTable;
