import { useState, useEffect, useMemo } from 'react';
import {
    Accordion,
    AccordionDetails,
    AccordionSummary,
    Box,
    Chip,
    FormControl,
    InputLabel,
    MenuItem,
    OutlinedInput,
    Select,
    Typography,
} from '@mui/material';
import { useAppContext } from '../../../src/render.jsx';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlusIcon from '@mui/icons-material/Add';
import CreateInstructorForm from './CreateInstructorForm';


function AddInstructorsSection({ onChangeCallback, activeOrganizationId, initialInstructorIds = [] }) {
    const [orgInstructors, setOrgInstructors] = useState([]);
    const [selectedIds, setSelectedIds] = useState(initialInstructorIds);
    const [expanded, setExpanded] = useState(false);
    const { localeMessages, apiBaseUrl } = useAppContext();

    const hasInstructors = useMemo(() => orgInstructors.length > 0, [orgInstructors]);

    const switchExpanded = () => {
        if (hasInstructors) {
            setExpanded(!expanded);
        }
    };

    useEffect(() => {
        fetch(`${apiBaseUrl}/organizations/${activeOrganizationId}/users/`, {
            method: 'GET',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
        })
            .then((response) => response.json())
            .then((data) => {
                const instructors = (data.organization_users || []).filter(
                    (u) => u.can_act_as_instructor
                );
                setOrgInstructors(instructors);
                if (instructors.length === 0) {
                    setExpanded(true);
                }
            })
            .catch((error) => {
                console.error('Error fetching organization users:', error);
            });
    }, []);

    const handleSelectionChange = (event) => {
        const value = event.target.value;
        setSelectedIds(value);
        if (onChangeCallback) {
            onChangeCallback(value);
        }
    };

    return (
        <div>
            {hasInstructors && (
                <FormControl sx={{ mb: 2, minWidth: '100%' }}>
                    <InputLabel id="instructor-select-label">
                        {localeMessages['select_instructors']}
                    </InputLabel>
                    <Select
                        labelId="instructor-select-label"
                        multiple
                        value={selectedIds}
                        onChange={handleSelectionChange}
                        input={<OutlinedInput label={localeMessages['select_instructors']} />}
                        renderValue={(selected) => (
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                {selected.map((id) => {
                                    const instructor = orgInstructors.find((i) => i.id === id);
                                    return instructor ? (
                                        <Chip
                                            key={id}
                                            label={instructor.email}
                                            size="small"
                                            onDelete={(e) => {
                                                e.stopPropagation();
                                                const updatedIds = selectedIds.filter((i) => i !== id);
                                                setSelectedIds(updatedIds);
                                                if (onChangeCallback) onChangeCallback(updatedIds);
                                            }}
                                            onMouseDown={(e) => e.stopPropagation()}
                                        />
                                    ) : null;
                                })}
                            </Box>
                        )}
                    >
                        {orgInstructors.map((instructor) => (
                            <MenuItem key={instructor.id} value={instructor.id}>
                                {instructor.email}
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>
            )}
            <Accordion expanded={expanded} onChange={switchExpanded}>
                <AccordionSummary
                    expandIcon={hasInstructors ? <ExpandMoreIcon /> : null}
                    aria-controls="new-instructor-content"
                    id="new-instructor-header"
                >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PlusIcon />
                        <Typography component="span">{localeMessages['new_instructor']}</Typography>
                    </Box>
                </AccordionSummary>
                <AccordionDetails>
                    <CreateInstructorForm
                        activeOrganizationId={activeOrganizationId}
                        onSuccess={(newOrgUser) => {
                            const updatedInstructors = [...orgInstructors, newOrgUser];
                            setOrgInstructors(updatedInstructors);
                            const updatedIds = [...selectedIds, newOrgUser.id];
                            setSelectedIds(updatedIds);
                            if (onChangeCallback) {
                                onChangeCallback(updatedIds);
                            }
                            setExpanded(false);
                        }}
                    />
                </AccordionDetails>
            </Accordion>
        </div>
    );
}

export default AddInstructorsSection;
