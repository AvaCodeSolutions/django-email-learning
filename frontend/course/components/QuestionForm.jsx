import { useState, useRef, useEffect, use } from 'react';
import { Box, Grid, Typography, Button, Switch, Table, TableHead, TableBody, TableRow, TableCell, TextField } from '@mui/material';
import RuleIcon from '@mui/icons-material/Rule';
import EditIcon from '@mui/icons-material/Edit';
import ClearIcon from '@mui/icons-material/Clear';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';



const QuestionForm = ({question, index, deleteCallback}) => {
    const [questionText, setQuestionText] = useState(question.question);
    const [options, setOptions] = useState(question.options || []);
    const [editMode, setEditMode] = useState(false);
    const [addingOption, setAddingOption] = useState(false);
    const optionInputRef = useRef(null);

    const editQuestion = () => {
        if (editMode && questionText.trim() === '') {
            return;
        }
        setEditMode(!editMode);
    }

    useEffect(() => {
        if (addingOption && optionInputRef.current) {
            optionInputRef.current.focus();
        }
    }, [addingOption]);

    const addToOptions = (optionText) => {
        if (optionText.trim() !== "") {
            setOptions([...options, {"optionText": optionText.trim(), "isCorrect": false}]);
        }
        setAddingOption(false);
    }

    const updateOption = (optionIndex, isCorrect) => {
        const updatedOptions = options.map((option, idx) =>
            idx === optionIndex ? { ...option, isCorrect: isCorrect } : option
        );
        setOptions(updatedOptions);
    }


    return (
       <Box key={index} sx={{ mb: 1, p: 2, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
            <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, md: 9 }}>
                    <EditIcon sx={{borderRadius: "50%", display: "inline-block", float: "left", mr: 1, fontSize: "0.9rem", border: 1, borderColor: "grey.200", color: "grey.400", padding: "4px", cursor: "pointer", ':hover': { backgroundColor: "primary.main", color: "white", borderColor: "primary.main" } }} onClick={editQuestion}/>
                    {!editMode ? (
                        <Typography onClick={editQuestion}>{index + 1}. {questionText}</Typography>
                    ) : (
                        <TextField
                            variant="standard"
                            sx={{ ml: 1, float: "left", width: '95%', pt: 0 }}
                            value={questionText}
                            onChange={(e) => setQuestionText(e.target.value)}
                            onKeyDown={(e) => {if (e.key === 'Enter') { editQuestion(); }}}
                            autoFocus
                            helperText={!questionText ? "Question can not be empty": ""}
                        />
                    )}
                </Grid>
                <Grid size={{ xs: 12, md: 3 }} sx={{ textAlign: 'right' }}>
                    <Button variant="outlined" color="primary" sx={{ fontSize: '0.75rem', mt: 1 }} onClick={() => setAddingOption(true)} >
                        <RuleIcon /><Typography variant="button" sx={{ ml: 1, fontSize: '0.75rem' }}>Add Option</Typography>
                    </Button>
                    <Button variant="outlined" color="secondary" onClick={deleteCallback} sx={{ ml: 1, mt: 1, fontSize: '0.75rem' }}>
                        Delete
                    </Button>
                </Grid>
                {addingOption && (<>
                    <Grid size={{ xs: 9 }} sx={{ display: 'flex', alignItems: 'center' }}>
                        <TextField
                            fullWidth
                            inputRef={optionInputRef}
                            variant="outlined"
                            label="Option Text"
                            sx={{ mt: 1, width: '100%' }}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    addToOptions(e.target.value);
                                }
                            }}
                        />
                    </Grid>
                    <Grid size={{ xs: 3 }} sx={{ textAlign: 'left' }} alignItems={"center"}>
                        <Button variant="outlined" color="primary" sx={{ mt: 1, mr: 1 }} onClick={() => {
                            if (optionInputRef.current) {
                                console.log(optionInputRef.current);
                                addToOptions(optionInputRef.current.value);
                            }
                        }}>
                            <AddCircleOutlineIcon sx={{ mr: 1 }} />
                            Add
                        </Button>
                    </Grid>
                    </>
                )}
                <Grid size={{ xs: 12 }}>
                    { options.length > 0 && <Box sx={{ mt: 2 }}>
                        <Table>
                            <TableHead variant="head">
                                <TableRow>
                                    <TableCell>Options</TableCell>
                                    <TableCell>Correct Answer</TableCell>
                                    <TableCell align='right'>Actions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {options.map((option, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell>{option.optionText}</TableCell>
                                        <TableCell><Switch onChange={(e)=>updateOption(idx, e.target.checked)} /></TableCell>
                                        <TableCell align='right'>
                                            <EditIcon sx={{ cursor: 'pointer', mr: 1 }} onClick={() => {
                                                const newOptionText = prompt("Edit option text:", option.optionText);
                                                if (newOptionText !== null && newOptionText.trim() !== "") {
                                                    const updatedOptions = options.map((opt, i) => i === idx ? { ...opt, optionText: newOptionText.trim() } : opt);
                                                    setOptions(updatedOptions);
                                                }
                                            }} />
                                            <ClearIcon sx={{ cursor: 'pointer' }} onClick={() => {
                                                const updatedOptions = options.filter((_, i) => i !== idx);
                                                setOptions(updatedOptions);
                                            }} />
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </Box> }
                </Grid>
            </Grid>
        </Box>
    );
}

export default QuestionForm;
