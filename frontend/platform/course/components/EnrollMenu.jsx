import { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../../../src/render.jsx';
import PersonAddAlt1Icon from '@mui/icons-material/PersonAddAlt1';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import { getCookie } from '../../../src/utils.js';
import { Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Menu, MenuItem, Alert } from '@mui/material';


const EnrollMenu = ({successCallback}) => {
    const {courseId, localeMessages, direction, apiBaseUrl } = useAppContext();
    const [enrollMenuAnchorEl, setEnrollMenuAnchorEl] = useState(null);
    const [manualEnrollOpen, setManualEnrollOpen] = useState(false);
    const [manualEnrollEmail, setManualEnrollEmail] = useState('');
    const [manualEnrollError, setManualEnrollError] = useState('');
    const [manualEnrollSubmitting, setManualEnrollSubmitting] = useState(false);
    const manualEnrollInputRef = useRef(null);
    const enrollMenuListRef = useRef(null);

    const organizationId = localStorage.getItem('activeOrganizationId');

    useEffect(() => {
        if (manualEnrollOpen && manualEnrollInputRef.current) {
            manualEnrollInputRef.current.focus();
        }
    }, [manualEnrollOpen]);

    const isEnrollMenuOpen = Boolean(enrollMenuAnchorEl);

    const openEnrollMenu = (event) => {
        setEnrollMenuAnchorEl(event.currentTarget);
    }

    const closeEnrollMenu = () => {
        setEnrollMenuAnchorEl(null);
    }

    const handleEnrollMenuKeyDown = (event) => {
        if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') {
            return;
        }

        const menuItems = enrollMenuListRef.current?.querySelectorAll('[role="menuitem"]:not([aria-disabled="true"])');
        if (!menuItems || menuItems.length === 0) {
            return;
        }

        event.preventDefault();

        const items = Array.from(menuItems);
        const currentIndex = items.findIndex((item) => item === document.activeElement);
        const directionStep = event.key === 'ArrowDown' ? 1 : -1;
        const fallbackIndex = directionStep === 1 ? 0 : items.length - 1;
        const nextIndex = currentIndex === -1
            ? fallbackIndex
            : (currentIndex + directionStep + items.length) % items.length;

        items[nextIndex].focus();
    }

    const openManualEnrollDialog = () => {
        closeEnrollMenu();
        setManualEnrollError('');
        setManualEnrollEmail('');
        setManualEnrollOpen(true);
    }

    const closeManualEnrollDialog = () => {
        if (manualEnrollSubmitting) {
            return;
        }
        setManualEnrollOpen(false);
        setManualEnrollError('');
    }

    const submitManualEnrollment = async () => {
        const email = manualEnrollEmail.trim();
        if (!email) {
            setManualEnrollError(localeMessages['email_required'] || 'Email is required.');
            return;
        }

        setManualEnrollSubmitting(true);
        setManualEnrollError('');

        try {
            const response = await fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/enrollments/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    learner_email: email,
                })
            });

            const data = await response.json();

            if (!response.ok) {
                setManualEnrollError(data?.error || (localeMessages['enrollment_failed'] || 'Failed to enroll learner.'));
                return;
            }
            successCallback();
            setManualEnrollEmail('');
            setManualEnrollOpen(false);
        } catch (error) {
            console.error('Error enrolling learner:', error);
            setManualEnrollError(localeMessages['enrollment_failed'] || 'Failed to enroll learner.');
        } finally {
            setManualEnrollSubmitting(false);
        }
    }

    return (<>
            <Button
                variant="outlined"
                startIcon={<PersonAddAlt1Icon sx={{ marginLeft: direction == 'rtl' ? 1 : 0 }} />}
                endIcon={<ArrowDropDownIcon />}
                sx={{
                    marginBottom: 2,
                    minWidth: 190,
                    justifyContent: 'flex-start',
                    '& .MuiButton-endIcon': {
                        marginInlineStart: 'auto',
                        marginInlineEnd: 0,
                    },
                }}
                onClick={openEnrollMenu}
                >
                {localeMessages['enroll_learner'] }
            </Button>
            <Menu
                anchorEl={enrollMenuAnchorEl}
                open={isEnrollMenuOpen}
                onClose={closeEnrollMenu}
                disableRestoreFocus
                slotProps={{
                    list: {
                        ref: enrollMenuListRef,
                        onKeyDown: handleEnrollMenuKeyDown,
                        autoFocus: true,
                        sx: {
                            minWidth: 200,
                            py: 0,
                        }
                    },
                    paper: {
                        sx: {
                            marginTop: "1px",
                            border: '1px solid',
                            borderColor: 'border.main',
                        }
                    }
                }}
                >
                <MenuItem onClick={openManualEnrollDialog} sx={{ fontSize: '0.87rem', px: 1 }}>
                    {localeMessages['manual_email']}
                </MenuItem>
            </Menu>

            <Dialog
                open={manualEnrollOpen}
                onClose={closeManualEnrollDialog}
                fullWidth
                maxWidth="sm"
                TransitionProps={{
                    onEntered: () => {
                        manualEnrollInputRef.current?.focus();
                    }
                }}
            >
                <DialogTitle>{localeMessages['enroll_learner'] || 'Enroll Learner'}</DialogTitle>
                <DialogContent>
                    <TextField
                        fullWidth
                        autoFocus
                        inputRef={manualEnrollInputRef}
                        margin="dense"
                        type="email"
                        label={localeMessages['email'] || 'Email'}
                        value={manualEnrollEmail}
                        onChange={(event) => setManualEnrollEmail(event.target.value)}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter') {
                                event.preventDefault();
                                submitManualEnrollment();
                            }
                        }}
                        disabled={manualEnrollSubmitting}
                    />
                    {manualEnrollError && <Alert severity="error" sx={{ mt: 2 }}>{manualEnrollError}</Alert>}
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeManualEnrollDialog} disabled={manualEnrollSubmitting}>
                        {localeMessages['cancel'] || 'Cancel'}
                    </Button>
                    <Button variant="contained" onClick={submitManualEnrollment} disabled={manualEnrollSubmitting}>
                        {localeMessages['enroll'] || 'Enroll'}
                    </Button>
                </DialogActions>
            </Dialog>
        </>)
}

export default EnrollMenu;
