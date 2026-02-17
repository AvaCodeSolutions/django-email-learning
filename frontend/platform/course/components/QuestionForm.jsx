import { useState, useRef, useEffect, use } from 'react';
import { Box, Grid, Typography, Button, Switch, Table, TableHead, TableBody, TableRow, TableCell, TextField } from '@mui/material';
import RuleIcon from '@mui/icons-material/Rule';
import EditIcon from '@mui/icons-material/Edit';
import ClearIcon from '@mui/icons-material/Clear';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import { useAppContext } from '../../../src/render';


const QuestionForm = ({question, index, eventHandler}) => {
    const [questionText, setQuestionText] = useState(question.text);
    const [options, setOptions] = useState(question.options || []);
    const [editMode, setEditMode] = useState(false);
    const [addingOption, setAddingOption] = useState(false);
    const optionInputRef = useRef(null);

    const { userRole, localeMessages } = useAppContext();

    const editQuestion = () => {
        if (editMode && questionText.trim() === '' || userRole === 'viewer') {
            return;
        }
        triggerUpdateEvent();
        setEditMode(!editMode);
    }

    const triggerUpdateEvent = () => {
        console.log("Triggering update event for question index " + index + " with options" + JSON.stringify(options));
        eventHandler({type: 'update_question', question_index: index, question_data: {'text': questionText, 'options': options}});
    }

    const deleteCallback = () => {
        eventHandler({type: 'delete_question', question_index: index});
    }

    useEffect(() => {
        if (addingOption && optionInputRef.current) {
            optionInputRef.current.focus();
        }
    }, [addingOption]);

    useEffect(() => {
        triggerUpdateEvent();
    }, [options, questionText]);

    const addToOptions = (optionText) => {
        if (optionText.trim() !== "") {
            setOptions([...options, {"optionText": optionText.trim(), "isCorrect": false, "editMode": false}]);
        }
        setAddingOption(false);
    }

    const updateOption = async (optionIndex, isCorrect) => {
        const updatedOptions = options.map((option, idx) =>
            idx === optionIndex ? { ...option, isCorrect: isCorrect } : option
        );
        await setOptions(updatedOptions);
        console.log("Updated Options:", updatedOptions);
    }


    return (
       <Box key={index} sx={{ mb: 1, p: 2, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
            <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, md: 9 }}>
                    {userRole !== 'viewer' && <EditIcon sx={{borderRadius: "50%", display: "inline-block", float: "left", mr: 1, fontSize: "0.9rem", border: 1, borderColor: "grey.200", color: "grey.400", padding: "4px", cursor: "pointer", ':hover': { backgroundColor: "primary.main", color: "white", borderColor: "primary.main" } }} onClick={editQuestion}/>}
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
                    {userRole !== 'viewer' && <><Button variant="outlined" color="primary" sx={{ fontSize: '0.75rem', mt: 1 }} onClick={() => setAddingOption(true)} >
                        <RuleIcon /><Typography variant="button" sx={{ ml: 1, fontSize: '0.75rem' }}>{localeMessages["add_option"]}</Typography>
                    </Button>
                    <Button variant="outlined" onClick={deleteCallback} sx={{ mx: 1, mt: 1, fontSize: '0.75rem' }}>
                        {localeMessages["delete"]}
                    </Button></>}
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
                                if (e.key === 'Escape') {
                                    setAddingOption(false);
                                }
                            }}
                        />
                    </Grid>
                    <Grid size={{ xs: 3 }} sx={{ textAlign: 'left' }} alignItems={"center"}>
                        <Button variant="outlined" sx={{ mt: 1, mr: 1 }} onClick={() => {
                            if (optionInputRef.current) {
                                console.log(optionInputRef.current);
                                addToOptions(optionInputRef.current.value);
                            }
                        }}>
                            <AddCircleOutlineIcon sx={{ mr: 1 }} />
                            { localeMessages["add"] }
                        </Button>
                        <Button variant="outlined" sx={{ mt: 1 }} onClick={() => setAddingOption(false)}>
                            { localeMessages["cancel"] }
                        </Button>
                    </Grid>
                    </>
                )}
                <Grid size={{ xs: 12 }}>
                    { options.length > 0 && <Box sx={{ mt: 2 }}>
                        <Table>
                            <TableHead variant="head">
                                <TableRow>
                                    <TableCell>{localeMessages["options"]}</TableCell>
                                    <TableCell>{localeMessages["correct_answer"]}</TableCell>
                                    {userRole !== 'viewer' && <TableCell align='right'>{localeMessages["actions"]}</TableCell>}
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {options.map((option, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell>{!option.editMode ? <Typography onClick={() => {
                                            setOptions(options.map((opt, i) => i === idx ? { ...opt, editMode: !opt.editMode } : opt));
                                        }}>{option.optionText}</Typography> : (
                                            <TextField
                                                fullWidth
                                                variant="outlined"
                                                defaultValue={option.optionText}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') {
                                                        const updatedOptions = options.map((opt, i) => i === idx ? { ...opt, optionText: e.target.value, editMode: false } : opt);
                                                        setOptions(updatedOptions);
                                                    }
                                                }}
                                            />
                                        )}</TableCell>
                                        <TableCell><Switch onChange={(e)=>updateOption(idx, e.target.checked)} checked={option.isCorrect} disabled={userRole === 'viewer'} /></TableCell>
                                        {userRole !== 'viewer' && <TableCell align='right'>
                                            <EditIcon sx={{ cursor: 'pointer', mr: 1 }} onClick={() => {
                                                setOptions(options.map((opt, i) => i === idx ? { ...opt, editMode: !opt.editMode } : opt));
                                            }} />
                                            <ClearIcon sx={{ cursor: 'pointer' }} onClick={() => {
                                                const updatedOptions = options.filter((_, i) => i !== idx);
                                                setOptions(updatedOptions);
                                            }} />
                                        </TableCell>}
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
