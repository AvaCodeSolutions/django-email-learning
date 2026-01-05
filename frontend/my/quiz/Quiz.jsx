import render from '../../src/render.jsx';
import { useState } from 'react';
import { Alert, Box, Button, Checkbox, FormControlLabel, GlobalStyles, Typography, Dialog } from '@mui/material';
import CelebrationIcon from '@mui/icons-material/Celebration';
import SentimentVeryDissatisfiedIcon from '@mui/icons-material/SentimentVeryDissatisfied';


const Quiz = () => {

    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedAnswers, setSelectedAnswers] = useState(quiz? quiz.questions.map(q => ({"id": q.id, "answers": []})) : []);
    const [warning, setWarning] = useState("");
    const [showQuestions, setShowQuestions] = useState(true);
    const [isPassed, setIsPassed] = useState(null);
    const [score, setScore] = useState(null);

    if (error_message) {
        console.log("Error:", error_message, ref);
    } else {
        console.log("No error");
    }

    const showSubmitDialog = () => {
        setDialogOpen(true);
        let answerCounter = 0;
        for (let i = 0; i < selectedAnswers.length; i++) {
            answerCounter += selectedAnswers[i].answers.length;
        }
        if (answerCounter === 0) {
            setWarning("You have not selected any answers. Are you sure you want to submit an empty quiz?");
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
        })
        .catch(() => {
            console.error("Error submitting quiz");
        });
    }


    return <>
    <GlobalStyles styles={(theme) => ({ body: { margin: 0, padding: 0, backgroundColor: theme.palette.background.dark, color: theme.palette.text.primary } })} />
    <Box textAlign="left" sx={{ maxWidth: 800, margin: '0 auto', backgroundColor: "background.light", height: 80 }}></Box>
    <Box sx={{ maxWidth: 800, margin: '0 auto', padding: 4, border: '1px solid #ccc', borderRadius: 2, backgroundColor: "background.paper" }} component="form" method="POST" action="">
        { !error_message ? <Box>
        <Box mb={4}>
        <Typography variant="h4" mb={1}>{quiz.title}</Typography>
        </Box>
        {showQuestions ? <Box>
        <Typography>
        Please select all correct answers for each question. Note that some questions may have multiple correct answers.
        This quiz uses negative marking for incorrect choices; if you are unsure, it is better to leave the question unanswered.
        </Typography>


        {quiz.questions.map((question, index) => (
            <Box key={index} sx={{marginBottom: 2, paddingTop: 1, borderBottom: "bacground.nav" }}>
                <Box mb={1}><Typography sx={{fontWeight: 'bold'}}>{question.text}</Typography></Box>
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
                    } }} />} label={answer.text} key={cIndex} sx={{display: 'block', fontSize: 'small'}}/>
                ))}
            </Box>
        ))}
        <Box mt={4} textAlign="center">
            <Button variant="contained" onClick={showSubmitDialog}>Submit</Button>
        </Box>
        </Box> : <Box textAlign="center">
            {isPassed !== null && (isPassed ? <Alert severity="success"><Typography variant="h6"><CelebrationIcon /> Congratulations! You have passed the quiz. Your score is {score}%.</Typography></Alert> :
            <Alert severity="error"><Typography variant="h6"><SentimentVeryDissatisfiedIcon /> Unfortunately, you did not pass the quiz. Your score is {score}%.</Typography></Alert>)}
        </Box>}
        </Box> : <Alert severity="error"><Typography variant="h6">Error loading quiz: {error_message} {ref && `(Ref: ${ref})`}</Typography></Alert>}
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
            <Box p={4}>
                <Typography variant="h6" mb={2}>Ready to submit?</Typography>
                {warning ? <Alert severity="warning" mb={2}><Typography>{warning}</Typography></Alert> :
                <Typography>Please keep in mind that this quiz uses negative marking for incorrect answers. If you are unsure of an answer, it may be better to leave it blank.</Typography>}
                <Box mt={4} textAlign="right">
                    <Button variant="text" onClick={() => setDialogOpen(false)} sx={{ mr: 2 }}>Cancel</Button>
                    <Button variant="contained" onClick={submitQuiz}>Submit</Button>
                </Box>
            </Box>
        </Dialog>
    </Box>
    </>
}

render({children: <Quiz />});
