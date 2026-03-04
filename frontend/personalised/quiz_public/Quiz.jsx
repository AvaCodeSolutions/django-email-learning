import render, { useAppContext } from '../../src/render.jsx';
import { use, useEffect, useState } from 'react';
import Layout from '../../public/components/Layout.jsx';
import { Alert, Box, Button, Checkbox, FormControlLabel, Typography, Dialog } from '@mui/material';
import CelebrationIcon from '@mui/icons-material/Celebration';
import SentimentVeryDissatisfiedIcon from '@mui/icons-material/SentimentVeryDissatisfied';


const Quiz = () => {
    const { localeMessages, token, csrfToken, apiEndpoint, errorMessage, quiz, ref, direction } = useAppContext();
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedAnswers, setSelectedAnswers] = useState(quiz? quiz.questions.map(q => ({"id": q.id, "answers": []})) : []);
    const [warning, setWarning] = useState("");
    const [showQuestions, setShowQuestions] = useState(true);
    const [isPassed, setIsPassed] = useState(null);
    const [message, setMessage] = useState("");
    const [score, setScore] = useState(null);


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
        })
        .catch(() => {
            console.error("Error submitting quiz");
        });
    }


    return <Layout>
    <Box sx={{ width: '100%', maxWidth: 920, mx: 'auto', p: { xs: 2, md: 4 }, borderRadius: 2, backgroundColor: "background.paper" }} component="form" method="POST" action="">
        { !errorMessage ? <Box>
        {showQuestions ? <><Box mb={3}>
        <Typography variant="h4" mb={1}>{quiz.title}</Typography>
        </Box>
        <Box>
        <Typography sx={{ mb: 3, color: 'text.secondary' }}>
        { localeMessages['quiz_intro'] }
        </Typography>


        {quiz.questions.map((question, index) => (
            <Box key={index} sx={{ mb: 2, py: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                <Box mb={1}><Typography sx={{ fontWeight: 'bold', lineHeight: 1.5 }}>{question.text}</Typography></Box>
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
        <Box mt={3.5} textAlign="center">
            <Button variant="contained" onClick={showSubmitDialog} sx={{px: 3, fontSize: '1.1rem'}}>{localeMessages['submit']}</Button>
        </Box>
        </Box></> : <Box textAlign="center">
            {isPassed !== null && (isPassed ? <><CelebrationIcon sx={{mb: 2, color: 'primary.main', fontSize: '3rem'}}/><Alert severity="success" sx={{justifyContent: 'center', alignItems: 'center'}} ><Typography variant='h6'>{message} {localeMessages['your_score']}: {score}%</Typography></Alert></> :
            <Alert severity="error" sx={{ justifyContent: 'center', alignItems: 'center' }} ><Typography variant="h6">{message} {localeMessages['your_score']}: {score}%</Typography></Alert>)}
            <Box sx={{mt: 6, fontSize: '0.8rem'}}><Typography>{localeMessages['close_window_message']}</Typography></Box>
        </Box>}
        </Box> : <Alert severity="error"><Typography variant="h6">{localeMessages['error']}: {errorMessage} {ref && `(Ref: ${ref})`}</Typography></Alert>}
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
            <Box p={4}>
                <Typography variant="h6" mb={2}>{localeMessages['ready_to_submit']}</Typography>
                {warning ? <Alert severity="warning" sx={{ mb: 2 }}><Typography>{warning}</Typography></Alert> :
                <Typography>{localeMessages['submit_quiz_note']}</Typography>}
                <Box mt={4} textAlign="right">
                    <Button variant="text" onClick={() => setDialogOpen(false)} sx={{ mr: 2 }}>{localeMessages['cancel']}</Button>
                    <Button variant="contained" onClick={submitQuiz}>{localeMessages['submit']}</Button>
                </Box>
            </Box>
        </Dialog>
    </Box>
    </Layout>
}

render({children: <Quiz />});
