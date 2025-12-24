import { useRef, useState, useEffect } from 'react';
import { Box, Button,  Grid, Typography } from '@mui/material';
import QuizIcon from '@mui/icons-material/Quiz';
import RequiredTextField from '../../src/components/RequiredTextField';
import QuestionForm from './QuestionForm';

const QuizForm = ({cancelCallback, successCallback, courseId, quizId }) => {

    const [showQuestionField, setShowQuestionField] = useState(false);
    const [newQuestion, setNewQuestion] = useState("");
    const [questions, setQuestions] = useState([]);
    const questionInputRef = useRef(null);
    const dialogRef = useRef(null);

    const addQuiz = () => {
        // Implement add quiz logic here
        console.log("Adding quiz to course ID:", courseId);
        // After successful addition
        successCallback();
    }

    const updateQuiz = () => {
        // Implement update quiz logic here
        console.log("Updating quiz ID:", quizId);
        // After successful update
        successCallback();
    }

    const cancel = () => {
        cancelCallback();
    }

    useEffect(() => {
        console.log('useEffect triggered, showQuestionField:', showQuestionField);
        if (!showQuestionField) {
            console.log('Focusing dialog');
            dialogRef.current?.focus();
        }
        if (showQuestionField) {
            console.log('Should focus question input, ref is:', questionInputRef.current);
            if (questionInputRef.current) {
                questionInputRef.current.focus();
            } else {
                console.log('questionInputRef.current is null!');
            }
        }
    }, [showQuestionField]);


    const addToQuestions = () => {

        if (newQuestion.trim() !== "") {
            setQuestions([...questions, {"question": newQuestion.trim()}]);
        }
        setNewQuestion("");
        setShowQuestionField(false);
    }

    const handleQuestionDelete = (index) => {
        const updatedQuestions = questions.filter((_, i) => i !== index);
        setQuestions(updatedQuestions);
    }

    return (
         <Box ref={dialogRef} sx={{ p: 3 }} onKeyDown={(e) => {
            if (e.key === 'q' && !showQuestionField) {
                setNewQuestion("");
                setTimeout(() => {
                    setShowQuestionField(true);
                }, 100);

            }
        }} tabIndex={0} focusable="true">
            <Typography variant="h2" sx={{ my: 2, fontSize: '1.5rem' }}>{ quizId ? "Update Quiz" : "New Quiz" }</Typography>
            <Button variant="outlined" sx={{ mb: 2 }} onClick={() => setShowQuestionField(true)}>
                <QuizIcon sx={{ mr: 1 }} /> Add Question</Button>
            { showQuestionField && (
                <Box sx={{ mb: 2, border: '1px solid', borderColor: 'grey.300', borderRadius: 1, p: 2 }}>
                    <Grid container spacing={2} alignItems="center">
                        <Grid size={{ xs: 12, md: 8 }}>
                            <RequiredTextField inputRef={questionInputRef} label="Question" value={newQuestion} onChange={(e) => setNewQuestion(e.target.value)} sx={{ width: '100%' }} onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    addToQuestions();
                                }
                            }}/>
                        </Grid>
                        <Grid size={{ xs: 12, md: 4 }} sx={{ textAlign: 'right' }}>
                            <Button variant="outlined" onClick={() => {
                                addToQuestions();
                            }}>
                                Add Question
                            </Button>
                            <Button variant="outlined" sx={{ ml: 1 }} onClick={() => { setShowQuestionField(false); setNewQuestion(""); }}>
                                Cancel
                            </Button>
                        </Grid>
                    </Grid>
                </Box>
            ) }
            <Box>
                { questions.map((question, index) => (
                    <QuestionForm key={index} index={index} question={question} deleteCallback={() => handleQuestionDelete(index)} />
                )) }
            </Box>
            <Box mt={2} textAlign="right">
                <Button variant="outlined" sx={{ mr: 1, boxShadow: 'none' }} onClick={cancel}>
                    Cancel
                </Button>
                <Button type="submit" variant="contained" color="primary" sx={{ boxShadow: 'none' }} onClick={() => {if(!quizId) { addQuiz(); } else { updateQuiz(); }}}>
                    Save Quiz
                </Button>
            </Box>
        </Box>
    );
}

export default QuizForm;
