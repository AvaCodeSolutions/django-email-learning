import { useRef, useState, useEffect } from 'react';
import { Alert,Box, Button, Grid, MenuItem, Select, Tooltip, Typography } from '@mui/material';
import QuizIcon from '@mui/icons-material/Quiz';
import RequiredTextField from '../../src/components/RequiredTextField';
import QuestionForm from './QuestionForm';
import { getCookie } from '../../src/utils';

const QuizForm = ({cancelCallback, successCallback, courseId, quizId, contentId, initialRequiredScore, initialTitle, initialQuestions, initialWaitingPeriod }) => {

    const [showQuestionField, setShowQuestionField] = useState(false);
    const [newQuestion, setNewQuestion] = useState("");
    const [questions, setQuestions] = useState(initialQuestions || []);
    const [errorMessage, setErrorMessage] = useState("");
    const [title, setTitle] = useState(initialTitle || "");
    const [requiredScore , setRequiredScore] = useState(initialRequiredScore || 70);
    const [waitingPeriod, setWaitingPeriod] = useState(initialWaitingPeriod ? initialWaitingPeriod.period : 1);
    const [waitingPeriodUnit, setWaitingPeriodUnit] = useState(initialWaitingPeriod ? initialWaitingPeriod.type : "days");
    const questionInputRef = useRef(null);
    const dialogRef = useRef(null);
    const apiBaseUrl = localStorage.getItem('apiBaseUrl');
    const organizationId = localStorage.getItem('activeOrganizationId');
    const userRole = localStorage.getItem('userRole');

    const addQuiz = () => {
        if (!validateQuiz()) {
            return;
        }
        console.log("Adding new quiz to course ID:", courseId);
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                content: {
                    type: 'quiz',
                    title: title,
                    required_score: requiredScore,
                    questions: questionsPayload(),
                },
                waiting_period: {
                    period: waitingPeriod,
                    type: waitingPeriodUnit
                }
            }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Quiz created successfully:', data);
            successCallback();
        })
        .catch(error => {
            setErrorMessage("Error creating quiz. Please try again.");
            console.error('Error creating quiz:', error);
        });

    }

    const validateQuiz = () => {
        if (title.trim() === "") {
            setErrorMessage("Quiz title cannot be empty.");
            return false;
        }
        if (questions.length === 0) {
            setErrorMessage("Quiz must contain at least one question.");
            return false;
        }
        for (let i = 0; i < questions.length; i++) {
            const question = questions[i];
            if (question.text.trim() === "") {
                setErrorMessage(`Question ${i + 1} cannot be empty.`);
                return false;
            }
            const options = question.options || [];
            if (options.length < 2) {
                setErrorMessage(`Question ${i + 1} must have at least two answer options.`);
                return false;
            }
            const hasCorrectOption = options.some(option => option.isCorrect);
            if (!hasCorrectOption) {
                setErrorMessage(`Question ${i + 1} must have at least one correct answer.`);
                return false;
            }
        }
        setErrorMessage("");
        return true;
    }

    const questionsPayload = () => {
        return questions.map((question, index) => ({
            text: question.text,
            answers: answersPayload(question.options || []),
            priority: index + 1,
        }));
    }

    const answersPayload = (options) => {
        return options.map((option) => ({
            text: option.optionText,
            is_correct: option.isCorrect,
        }));
    }

    const questionEventHandler = (event) => {
        if (event.type === 'delete_question') {
            const updatedQuestions = questions.filter((_, i) => i !== index);
            setQuestions(updatedQuestions);
        }
        if (event.type === 'update_question') {
            const updatedQuestions = questions.map((q, i) =>
                i === event.question_index ? event.question_data : q
            );
            console.log('Updated Questions:', updatedQuestions);
            setQuestions(updatedQuestions);
        }
    }

    const updateQuiz = () => {
        if (!validateQuiz()) {
            return;
        }
        console.log("Updating quiz ID:", quizId, "for course ID:", courseId);
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                quiz: {
                    title: title,
                    required_score: requiredScore,
                    questions: questionsPayload(),
                },
                waiting_period: {
                    period: waitingPeriod,
                    type: waitingPeriodUnit
                }}),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Quiz updated successfully:', data);
            successCallback();
        })
        .catch(error => {
            setErrorMessage("Error updating quiz. Please try again.");
            console.error('Error updating quiz:', error);
        });
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
            setQuestions([...questions, {"text": newQuestion.trim()}]);
        }
        setNewQuestion("");
        setShowQuestionField(false);
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
            {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
            <RequiredTextField label="Quiz Title" value={title} onChange={(e) => setTitle(e.target.value)} sx={{ mb: 2, width: '100%' }} disabled={userRole === 'viewer'} />
            {userRole !== 'viewer' && <Button variant="outlined" sx={{ mb: 2 }} onClick={() => setShowQuestionField(true)}>
                <QuizIcon sx={{ mr: 1 }} /> Add Question</Button>}
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
                    <QuestionForm key={index} index={index} question={question} eventHandler={questionEventHandler} />
                )) }
            </Box>
            <Box mt={3} mb={2}>
            <RequiredTextField
                label="Required score to pass (%)"
                type="number"
                value={requiredScore}
                onChange={(e) => setRequiredScore(e.target.value)}
                sx={{ width: '200px', mr: 2 }}
                inputProps={{ min: 0, max: 100 }}
                disabled={userRole === 'viewer'}
                >
            </RequiredTextField>
            </Box>
            <Tooltip
                placement="right"
                title="Set the amount of time that we should wait after the previous lesson or quiz submission before sending this lesson.">
                <RequiredTextField
                    label="Waiting Period"
                    name="waiting_period"
                    type="number"
                    value={waitingPeriod}
                    onChange={(e) => setWaitingPeriod(e.target.value)}
                    sx={{ width: '200px', mr: 2 }}
                    inputProps={{ min: 1 }}
                    disabled={userRole === 'viewer'}
                />
                <Select size="small" value={waitingPeriodUnit} onChange={(e) => setWaitingPeriodUnit(e.target.value)} name="waiting_period_unit" sx={{ width: '150px' }} disabled={userRole === 'viewer'}>
                    <MenuItem value="days">Days</MenuItem>
                    <MenuItem value="hours">Hours</MenuItem>
                </Select>
            </Tooltip>
            <Box mt={2} textAlign="right">
                <Button variant="outlined" sx={{ mr: 1, boxShadow: 'none' }} onClick={cancel}>
                    Back
                </Button>
                {userRole !== 'viewer' && <Button type="submit" variant="contained" color="primary" sx={{ boxShadow: 'none' }} onClick={() => {if(!quizId) { addQuiz(); } else { updateQuiz(); }}}>
                    Save Quiz
                </Button>}
            </Box>
        </Box>
    );
}

export default QuizForm;
