import render, { useAppContext } from '../../src/render.jsx';
import { use, useEffect, useState } from 'react';
import Layout from '../../public/components/Layout.jsx';
import { Alert, Box, Button, Checkbox, Chip, FormControlLabel, Typography, Dialog } from '@mui/material';
import CelebrationIcon from '@mui/icons-material/Celebration';
import SentimentVeryDissatisfiedIcon from '@mui/icons-material/SentimentVeryDissatisfied';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';


const Quiz = () => {
    const { localeMessages, token, csrfToken, apiEndpoint, errorMessage, quiz, ref, direction } = useAppContext();
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedAnswers, setSelectedAnswers] = useState(quiz? quiz.questions.map(q => ({"id": q.id, "answers": []})) : []);
    const [warning, setWarning] = useState("");
    const [showQuestions, setShowQuestions] = useState(true);
    const [isPassed, setIsPassed] = useState(null);
    const [message, setMessage] = useState("");
    const [isInvalidated, setIsInvalidated] = useState(true);
    const [score, setScore] = useState(null);
    const [quizData, setQuizData] = useState(null);


    const showSubmitDialog = () => {
        setDialogOpen(true);
        let answerCounter = 0;
        for (let i = 0; i < selectedAnswers.length; i++) {
            answerCounter += selectedAnswers[i].answers.length;
        }
        if (answerCounter === 0) {
            setWarning(localeMessages['no_answer_warning']);
        } else {
            setWarning("");
        }
    }

    const submitQuiz = () => {
        fetch(`${apiEndpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ token: token, answers: selectedAnswers }),
        })
        .then((response) => response.json())
        .then((data) => {
           setDialogOpen(false);
           setShowQuestions(false);
           setIsPassed(data.passed);
           setScore(data.score);
           setMessage(data.message);
           setIsInvalidated(data.is_invalidated);
           setQuizData(data.quiz_data || null);
        })
        .catch(() => {
            console.error("Error submitting quiz");
        });
    }

    const answerVisualState = (answer) => {
        if (answer.is_correct && answer.user_selected) {
            return {
                icon: <CheckCircleIcon fontSize="small" sx={{ color: 'success.main' }} />,
                chips: [{ label: localeMessages['correct_answer'] || 'Correct answer', color: 'success' }],
                color: 'success.main',
                backgroundColor: (theme) => theme.palette.mode === 'dark' ? 'rgba(76, 175, 80, 0.16)' : 'rgba(129, 199, 132, 0.28)',
                borderColor: 'success.main',
            };
        }
        if (answer.is_correct) {
            return {
                icon: <CheckCircleIcon fontSize="small" sx={{ color: 'success.main' }} />,
                chips: [{ label: localeMessages['correct_answer'] || 'Correct answer', color: 'success' }],
                color: 'success.main',
                backgroundColor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.02)' : 'rgba(0, 0, 0, 0.02)',
                borderColor: 'success.light',
            };
        }
        if (answer.user_selected) {
            return {
                icon: <CancelIcon fontSize="small" sx={{ color: 'error.main' }} />,
                chips: [],
                color: 'error.main',
                backgroundColor: (theme) => theme.palette.mode === 'dark' ? 'rgba(244, 67, 54, 0.14)' : 'rgba(244, 67, 54, 0.08)',
                borderColor: 'error.light',
            };
        }
        return {
            icon: <RadioButtonUncheckedIcon fontSize="small" sx={{ color: 'text.disabled' }} />,
            chips: [],
            color: 'text.primary',
            backgroundColor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.02)' : 'rgba(0, 0, 0, 0.02)',
            borderColor: 'divider',
        };
    };


    return <Layout>
    <Box sx={{ width: '100%', maxWidth: 920, mx: 'auto', p: { xs: 2, md: 4 }, borderRadius: 2, backgroundColor: "background.paper" }} component="form" method="POST" action="">
        { !errorMessage ? <Box>
        {showQuestions ? <><Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>{quiz.title}</Typography>
        </Box>
        <Box>
        <Typography sx={{ mb: 3, color: 'text.secondary' }}>
        { localeMessages['quiz_intro'] }
        </Typography>


        {quiz.questions.map((question, index) => (
            <Box key={index} sx={{ mb: 2, py: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ mb: 1 }}><Typography sx={{ fontWeight: 'bold', lineHeight: 1.5 }}>{question.text}</Typography></Box>
                {question.answers.map((answer, cIndex) => (
                    <FormControlLabel control={<Checkbox onChange={(e) => { if (!e.target.checked) {
                        const newSelectedAnswers = [...selectedAnswers];
                        const questionAnswers = newSelectedAnswers.find(qa => qa.id === question.id);
                        questionAnswers.answers = questionAnswers.answers.filter(aid => aid !== answer.id);
                        setSelectedAnswers(newSelectedAnswers);
                    } else {
                        const newSelectedAnswers = [...selectedAnswers];
                        const questionAnswers = newSelectedAnswers.find(qa => qa.id === question.id);
                        questionAnswers.answers.push(answer.id);
                        setSelectedAnswers(newSelectedAnswers);
                    } }} />} label={answer.text} key={cIndex} sx={{ display: 'block', alignItems: 'flex-start', my: 0.25 }} />
                ))}
            </Box>
        ))}
        <Box sx={{ mt: 3.5, textAlign: 'center' }}>
            <Button variant="contained" onClick={showSubmitDialog} sx={{px: 3, fontSize: '1.1rem'}}>{localeMessages['submit']}</Button>
        </Box>
        </Box></> : <Box sx={{ textAlign: 'center' }}>
            {isPassed !== null && (isPassed ? <>{ !quizData && <CelebrationIcon sx={{mb: 2, color: 'primary.main', fontSize: '3rem'}}/> }<Alert severity={ score == 100 ? "success" : "info" } sx={{justifyContent: 'center', alignItems: 'center'}} ><Typography variant='h6'>{message} {localeMessages['your_score']}: {score}%</Typography></Alert></> :
            <><Alert severity="error" sx={{ justifyContent: 'center', alignItems: 'center' }} ><Typography variant="h6">{message} {localeMessages['your_score']}: {score}%</Typography></Alert>
            {!isInvalidated && <Box sx={{ mt: 3, textAlign: 'center' }}><Button onClick={() => window.location.reload()} variant="contained">{localeMessages['try_again']}</Button></Box>}
            </>)}
            {quizData && (
                <Box sx={{ mt: 3, textAlign: direction === 'rtl' ? 'right' : 'left', border: '1px solid', borderColor: 'divider', borderRadius: 2, p: { xs: 2, md: 3 }, backgroundColor: 'background.default' }}>
                    <Typography variant="h6" sx={{ mb: 2 }}>
                        {quizData.title}
                    </Typography>
                    {quizData.questions?.map((question, qIndex) => (
                        <Box key={qIndex} sx={{ mb: 2.5, pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                            <Typography sx={{ fontWeight: 700, mb: 1.25 }}>
                                {question.text}
                            </Typography>
                            {question.answers?.map((answer, aIndex) => {
                                const visualState = answerVisualState(answer);
                                return (
                                    <Box
                                        key={aIndex}
                                        sx={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 1,
                                            border: '1px solid',
                                            borderColor: visualState.borderColor,
                                            backgroundColor: visualState.backgroundColor,
                                            borderRadius: 1,
                                            px: 1.25,
                                            py: 0.75,
                                            mb: 0.75,
                                        }}
                                    >
                                        {visualState.icon}
                                        <Typography sx={{ color: visualState.color, flex: 1 }}>
                                            {answer.text}
                                        </Typography>
                                        {visualState.chips.map((chip, chipIndex) => (
                                            <Chip key={chipIndex} label={chip.label} size="small" color={chip.color} />
                                        ))}
                                    </Box>
                                );
                            })}
                        </Box>
                    ))}
                </Box>
            )}
            { !quiz.is_blocking && <Box sx={{mt: 4}}><Typography>{localeMessages['non_blocking_quiz_caption']}</Typography></Box>}
            <Box sx={{mt: 6, fontSize: '0.8rem'}}>{ isInvalidated && <Typography>{localeMessages['close_window_message']}</Typography>}</Box>
        </Box>}
        </Box> : <Alert severity="error"><Typography variant="h6">{localeMessages['error']}: {errorMessage} {ref && `(Ref: ${ref})`}</Typography></Alert>}
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
            <Box sx={{ p: 4 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>{localeMessages['ready_to_submit']}</Typography>
                {warning ? <Alert severity="warning" sx={{ mb: 2 }}><Typography>{warning}</Typography></Alert> :
                <Typography>{localeMessages['submit_quiz_note']}</Typography>}
                <Box sx={{ mt: 4, textAlign: 'right' }}>
                    <Button variant="text" onClick={() => setDialogOpen(false)} sx={{ mr: 2 }}>{localeMessages['cancel']}</Button>
                    <Button variant="contained" onClick={submitQuiz}>{localeMessages['submit']}</Button>
                </Box>
            </Box>
        </Dialog>
    </Box>
    </Layout>
}

export { Quiz };
render({children: <Quiz />});
