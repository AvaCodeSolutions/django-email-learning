import { useRef, useState, useEffect } from 'react';
import { Alert,Box, Button, FormControlLabel, Grid, InputLabel, MenuItem, Select, Switch, Tooltip, Typography, Dialog } from '@mui/material';
import QuizIcon from '@mui/icons-material/Quiz';
import RequiredTextField from '../../../src/components/RequiredTextField';
import QuestionForm from './QuestionForm';
import { getCookie } from '../../../src/utils';
import { useAppContext } from '../../../src/render';

const QuizForm = ({cancelCallback, successCallback, courseId, quizId, contentId, initialRequiredScore, initialTitle, initialQuestions, initialWaitingPeriod, initialStrategy, initialDeadlineDays, initialLimitedAttempts, initialIsBlocking, initialReminderIntervalDays }) => {
    const questionIdRef = useRef(0);
    const createQuestionId = () => {
        questionIdRef.current += 1;
        return `question-${questionIdRef.current}`;
    };

    const [showQuestionField, setShowQuestionField] = useState(false);
    const [newQuestion, setNewQuestion] = useState("");
    const [questions, setQuestions] = useState(() => (initialQuestions || []).map((question) => ({
        ...question,
        _clientId: question._clientId || createQuestionId(),
    })));
    const [errorMessage, setErrorMessage] = useState("");
    const [title, setTitle] = useState(initialTitle || "");
    const [selectionStrategy, setSelectionStrategy] = useState(initialStrategy || "random");
    const { localeMessages, userRole, apiBaseUrl, quizDefaults = {} } = useAppContext();
    const initialIsBlockingValue = initialIsBlocking ?? quizDefaults.isBlocking ?? true;
    const [isBlocking, setIsBlocking] = useState(initialIsBlockingValue);
    const initialRequiredScoreValue = initialIsBlockingValue ? (initialRequiredScore ?? 70) : 0;
    const [requiredScore , setRequiredScore] = useState(initialRequiredScoreValue);
    const initialLimitedAttemptsValue = initialLimitedAttempts ?? quizDefaults.limitedAttempts ?? true;
    const [limitedAttempts, setLimitedAttempts] = useState(initialLimitedAttemptsValue);
    const [deadlineDays, setDeadlineDays] = useState(initialDeadlineDays || 14);
    const initialHasDeadline = initialDeadlineDays !== undefined ? (initialDeadlineDays > 0) : (quizDefaults.hasDeadline ?? false);
    const [hasDeadline, setHasDeadline] = useState(initialHasDeadline);
    const defaultReminderIntervalDays = Number(quizDefaults.reminderIntervalDays ?? 0);
    const initialReminderIntervalValue = !initialHasDeadline
        ? (initialReminderIntervalDays ?? (quizId ? 0 : defaultReminderIntervalDays))
        : 0;
    const initialReminderEnabled = Number(initialReminderIntervalValue) > 0;
    const [hasReminderInterval, setHasReminderInterval] = useState(initialReminderEnabled);
    const [reminderIntervalDays, setReminderIntervalDays] = useState(initialReminderIntervalValue);
    const [waitingPeriod, setWaitingPeriod] = useState(initialWaitingPeriod ? initialWaitingPeriod.period : 1);
    const [waitingPeriodUnit, setWaitingPeriodUnit] = useState(initialWaitingPeriod ? initialWaitingPeriod.type : "days");
    const questionInputRef = useRef(null);
    const dialogRef = useRef(null);
    const organizationId = localStorage.getItem('activeOrganizationId');
    const [confirmCloseDialogOpen, setConfirmCloseDialogOpen] = useState(false);
    const reminderIntervalDefaultValue = defaultReminderIntervalDays > 0 ? defaultReminderIntervalDays : 1;


    const compareQuestions = (questions1, questions2) => {
        if (questions1.length !== questions2.length) {
            return false;
        }
        for (let i = 0; i < questions1.length; i++) {
            const q1 = questions1[i];
            const q2 = questions2[i];
            if (q1.text !== q2.text) {
                return false;
            }
            const options1 = q1.options || [];
            const options2 = q2.options || [];
            if (options1.length !== options2.length) {
                return false;
            }
            for (let j = 0; j < options1.length; j++) {
                const o1 = options1[j];
                const o2 = options2[j];
                if (o1.optionText !== o2.optionText || o1.isCorrect !== o2.isCorrect) {
                    return false;
                }
            }
        }
        return true;
    }

    const hasUnsavedChanges = () => {
        if (!compareQuestions(questions, initialQuestions || []) || title !== initialTitle || requiredScore !== initialRequiredScoreValue || selectionStrategy !== initialStrategy || isBlocking !== initialIsBlockingValue || (isBlocking && limitedAttempts !== initialLimitedAttemptsValue) || deadlineDays !== initialDeadlineDays || hasDeadline !== initialHasDeadline || hasReminderInterval !== initialReminderEnabled || reminderIntervalDays !== initialReminderIntervalValue || waitingPeriod !== (initialWaitingPeriod ? initialWaitingPeriod.period : 1) || waitingPeriodUnit !== (initialWaitingPeriod ? initialWaitingPeriod.type : "days")) {
            console.log(questions, initialQuestions, title, initialTitle, requiredScore, initialRequiredScoreValue, selectionStrategy, initialStrategy, isBlocking, initialIsBlockingValue, limitedAttempts, initialLimitedAttemptsValue, deadlineDays, initialDeadlineDays, hasReminderInterval, initialReminderEnabled, reminderIntervalDays, initialReminderIntervalValue, waitingPeriod, (initialWaitingPeriod ? initialWaitingPeriod.period : 1), waitingPeriodUnit, (initialWaitingPeriod ? initialWaitingPeriod.type : "days"));
            return true;
        }
        return false;
    }

    const buildQuizPayload = () => {
        const finalDeadlineDays = hasDeadline ? deadlineDays : 0;
        const normalizedReminderIntervalDays = !hasDeadline && hasReminderInterval
            ? Number(reminderIntervalDays)
            : 0;
        const shouldClearReminderInterval = Boolean(quizId) && (initialReminderEnabled || Number(initialReminderIntervalValue) > 0) && normalizedReminderIntervalDays === 0;

        const quizPayload = {
            title: title,
            required_score: requiredScore,
            selection_strategy: selectionStrategy,
            deadline_days: finalDeadlineDays,
            is_blocking: isBlocking,
            questions: questionsPayload(),
        };

        if (!quizId) {
            quizPayload.type = 'quiz';
        }

        if (isBlocking) {
            quizPayload.limited_attempts = limitedAttempts;
        }

        if (normalizedReminderIntervalDays > 0) {
            quizPayload.reminder_interval_days = normalizedReminderIntervalDays;
        } else if (shouldClearReminderInterval) {
            quizPayload.reminder_interval_days = null;
        }

        return quizPayload;
    }

    const addQuiz = () => {
        if (!validateQuiz()) {
            return;
        }
        console.log("Adding new quiz to course ID:", courseId);
        const quizPayload = buildQuizPayload();
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                content: {
                    ...quizPayload,
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
        console.log("Validating quiz with title:", title, "and questions:", questions);
        if (title.trim() === "") {
            setErrorMessage(localeMessages["quiz_title_empty"]);
            return false;
        }
        if (questions.length === 0) {
            setErrorMessage(localeMessages["at_least_one_question"]);
            return false;
        }
        if (isBlocking && requiredScore === 0) {
            setErrorMessage(localeMessages["required_score_blocking"]);
            return false;
        }
        if (hasDeadline && (Number(deadlineDays) === 0 || deadlineDays === "")) {
            setErrorMessage(localeMessages["deadline_cannot_be_zero"] || "Deadline cannot be 0 when deadline is enabled");
            return false;
        }
        if (!hasDeadline && hasReminderInterval && (Number(reminderIntervalDays) <= 0 || reminderIntervalDays === "")) {
            setErrorMessage(localeMessages["reminder_interval_days_required"] || "Reminder interval days must be greater than 0 when reminders are enabled.");
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
                console.log("Options: " + JSON.stringify(options));
                setErrorMessage(localeMessages["at_least_two_options"].replace("QUESTION_NUMBER", i + 1));
                return false;
            }
            const hasCorrectOption = options.some(option => option.isCorrect);
            if (!hasCorrectOption) {
                setErrorMessage(localeMessages["at_least_one_correct"].replace("QUESTION_NUMBER", i + 1));
                return false;
            }
        }
        setErrorMessage("");
        return true;
    }

    const questionsPayload = () => {
        console.log("Generating questions payload for questions:", questions);
        console.log("Initial questions were:", initialQuestions);
        return questions.map((question, index) => ({
            id: question.id,
            text: question.text,
            answers: answersPayload(question.options || []),
            priority: index + 1,
        }));
    }

    const answersPayload = (options) => {
        return options.map((option) => ({
            id: option.id,
            text: option.optionText,
            is_correct: option.isCorrect,
        }));
    }

    const questionEventHandler = (event) => {
        if (event.type === 'delete_question') {
            setQuestions((currentQuestions) => currentQuestions.filter((question) => question._clientId !== event.question_id));
        }
        if (event.type === 'update_question') {
            const updatedQuestions = questions.map((question) =>
                question._clientId === event.question_id
                    ? { ...event.question_data, _clientId: question._clientId }
                    : question
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
        const quizPayload = buildQuizPayload();
        fetch(`${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/contents/${contentId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                quiz: {
                    ...quizPayload,
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

    useEffect(() => {
        if (!isBlocking && requiredScore !== 0) {
            setRequiredScore(0);
        }
    }, [isBlocking, requiredScore]);

    useEffect(() => {
        if (!hasDeadline && deadlineDays !== 0) {
            setDeadlineDays(0);
        }
    }, [hasDeadline, deadlineDays]);

    useEffect(() => {
        if (hasDeadline) {
            if (hasReminderInterval) {
                setHasReminderInterval(false);
            }
            if (reminderIntervalDays !== 0) {
                setReminderIntervalDays(0);
            }
        }
    }, [hasDeadline, hasReminderInterval, reminderIntervalDays]);


    const addToQuestions = () => {

        if (newQuestion.trim() !== "") {
            setQuestions([...questions, {"text": newQuestion.trim(), _clientId: createQuestionId(), id: null, options: []}]);
        }
        setNewQuestion("");
        setShowQuestionField(false);
    }

    return (
         <Box ref={dialogRef} sx={{ p: 3 }} tabIndex={0} focusable="true" onKeyDown={(e) => {
            if (e.key === 'Escape') {
                if (showQuestionField) {
                    setShowQuestionField(false);
                    setNewQuestion("");
                } else {
                    if (hasUnsavedChanges()) {
                        setConfirmCloseDialogOpen(true);
                    } else {
                        cancel();
                    }
                }
            }
        }}>
            <Typography variant="h2" sx={{ my: 2, fontSize: '1.5rem' }}>{ quizId ? localeMessages["update_quiz"] : localeMessages["new_quiz"] }</Typography>
            {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
            <RequiredTextField label={localeMessages["quiz_title"]} value={title} onChange={(e) => setTitle(e.target.value)} sx={{ mb: 2, width: '100%' }} disabled={userRole === 'viewer'} />
            {userRole !== 'viewer' && <Button variant="outlined" sx={{ mb: 2 }} onClick={() => setShowQuestionField(true)}>
                <QuizIcon sx={{ mr: 1 }} /> {localeMessages["add_question"]}</Button>}
            { showQuestionField && (
                <Box sx={{ mb: 2, border: '1px solid', borderColor: 'grey.300', borderRadius: 1, p: 2 }}>
                    <Grid container spacing={2} sx={{ alignItems: 'center' }}>
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
                                {localeMessages["add_question"]}
                            </Button>
                            <Button variant="outlined" sx={{ ml: 1 }} onClick={() => { setShowQuestionField(false); setNewQuestion(""); }}>
                                {localeMessages["cancel"]}
                            </Button>
                        </Grid>
                    </Grid>
                </Box>
            ) }
            <Box>
                { [...questions].reverse().map((question, index) => (
                    <QuestionForm key={question._clientId} index={index} question={question} eventHandler={questionEventHandler} />
                )) }
            </Box>
            {/* Quiz Settings Section */}
            <Box sx={{ mt: 3, mb: 3 }}>
                <Typography variant="h6" sx={{ mb: 2, fontSize: '1.1rem', color: 'secondary.main' }}>
                    {localeMessages["quiz_settings"]}
                </Typography>

                <Grid container spacing={3}>
                    {/* Row 1: Required Score and Waiting Period */}
                    <Grid size={{ xs: 12 }}>
                        <Box>
                            <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                {localeMessages["blocking_quiz"]}
                            </InputLabel>
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={isBlocking}
                                        onChange={(e) => setIsBlocking(e.target.checked)}
                                        disabled={userRole === 'viewer'}
                                    />
                                }
                                label={localeMessages["blocking_quiz"]}
                            />
                            <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.5 }}>
                                {localeMessages["blocking_quiz_tooltip"]}
                            </Typography>
                        </Box>
                    </Grid>

                    <Grid size={{ xs: 12, md: 6 }}>
                        <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                            {localeMessages["required_score"]}
                        </InputLabel>
                        <Tooltip
                            title={localeMessages["score_tooltip"]}
                            placement="top-start"
                        >
                            <RequiredTextField
                                label="percentage"
                                type="number"
                                value={requiredScore}
                                onChange={(e) => setRequiredScore(e.target.value)}
                                sx={{ width: '100%' }}
                                slotProps={{ htmlInput: { min: 0, max: 100 } }}
                                disabled={userRole === 'viewer' || !isBlocking}
                            />
                        </Tooltip>
                    </Grid>

                    <Grid size={{ xs: 12, md: 6 }}>
                        <Tooltip
                            title={localeMessages["period_tooltip"]}
                            placement="top-start"
                        >
                            <Box>
                                <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                    {localeMessages["waiting_period"]}
                                </InputLabel>
                                <Box sx={{ display: 'flex', gap: 1 }}>
                                    <RequiredTextField
                                        label="Period"
                                        type="number"
                                        value={waitingPeriod}
                                        onChange={(e) => setWaitingPeriod(e.target.value)}
                                        sx={{ flex: 1 }}
                                        slotProps={{ htmlInput: { min: 1 } }}
                                        disabled={userRole === 'viewer'}
                                    />
                                    <Select
                                        size="small"
                                        value={waitingPeriodUnit}
                                        onChange={(e) => setWaitingPeriodUnit(e.target.value)}
                                        sx={{ minWidth: '100px' }}
                                        disabled={userRole === 'viewer'}
                                    >
                                        <MenuItem value="days">Days</MenuItem>
                                        <MenuItem value="hours">Hours</MenuItem>
                                    </Select>
                                </Box>
                            </Box>
                        </Tooltip>
                    </Grid>

                    {/* Row 2: Deadline and Reminder Interval */}
                    <Grid size={{ xs: 12, md: 6 }}>
                        <Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                <InputLabel sx={{ fontSize: '0.9rem', color: 'text.secondary', m: 0 }}>
                                    {localeMessages["quiz_deadline"]}
                                </InputLabel>
                                <FormControlLabel
                                    control={
                                        <Switch
                                            checked={hasDeadline}
                                            onChange={(e) => {
                                                setHasDeadline(e.target.checked);
                                                if (!e.target.checked) {
                                                    setDeadlineDays(0);
                                                } else if (deadlineDays === 0 || deadlineDays === "0" || deadlineDays === "") {
                                                    setDeadlineDays(14);
                                                }
                                            }}
                                            disabled={userRole === 'viewer'}
                                            size="small"
                                        />
                                    }
                                    label=""
                                    sx={{ m: 0 }}
                                />
                            </Box>
                            <Tooltip
                                title={localeMessages["deadline_tooltip"]}
                                placement="top-start"
                            >
                                <RequiredTextField
                                    label="Days"
                                    type="number"
                                    value={deadlineDays}
                                    onChange={(e) => {
                                        if (hasDeadline) {
                                            setDeadlineDays(e.target.value);
                                        }
                                    }}
                                    sx={{ width: '100%' }}
                                    slotProps={{ htmlInput: { min: hasDeadline ? 1 : 0 } }}
                                    disabled={userRole === 'viewer' || !hasDeadline}
                                />
                            </Tooltip>
                        </Box>
                    </Grid>

                    {!hasDeadline && <Grid size={{ xs: 12, md: 6 }}>
                        <Tooltip
                            title={localeMessages["reminder_interval_days_tooltip"]}
                            placement="top-start"
                        >
                            <Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    <InputLabel sx={{ fontSize: '0.9rem', color: 'text.secondary', m: 0 }}>
                                        {localeMessages["reminder_interval_days"]}
                                    </InputLabel>
                                    <FormControlLabel
                                        control={
                                            <Switch
                                                checked={hasReminderInterval}
                                                onChange={(e) => {
                                                    setHasReminderInterval(e.target.checked);
                                                    if (!e.target.checked) {
                                                        setReminderIntervalDays(0);
                                                    } else if (reminderIntervalDays === 0 || reminderIntervalDays === "0" || reminderIntervalDays === "") {
                                                        setReminderIntervalDays(reminderIntervalDefaultValue);
                                                    }
                                                }}
                                                disabled={userRole === 'viewer'}
                                                size="small"
                                            />
                                        }
                                        label=""
                                        sx={{ m: 0 }}
                                    />
                                </Box>
                                <RequiredTextField
                                    label="Days"
                                    type="number"
                                    value={reminderIntervalDays}
                                    onChange={(e) => {
                                        if (hasReminderInterval) {
                                            setReminderIntervalDays(e.target.value);
                                        }
                                    }}
                                    sx={{ width: '100%' }}
                                    slotProps={{ htmlInput: { min: hasReminderInterval ? 1 : 0 } }}
                                    disabled={userRole === 'viewer' || !hasReminderInterval}
                                />
                            </Box>
                        </Tooltip>
                    </Grid>}

                    {/* Row 3: Selection Strategy */}
                    <Grid size={{ xs: 12, md: 6 }}>
                        <Tooltip
                            title={localeMessages["question_selection_strategy_tooltip"]}
                            placement="top-start"
                        >
                            <Box>
                                <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                    {localeMessages["question_selection_strategy"]}
                                </InputLabel>
                                <Select
                                    size="small"
                                    value={selectionStrategy}
                                    onChange={(e) => setSelectionStrategy(e.target.value)}
                                    sx={{ width: '100%' }}
                                    disabled={userRole === 'viewer'}
                                >
                                    <MenuItem value="all">{localeMessages["all_questions"]}</MenuItem>
                                    <MenuItem value="random">{localeMessages["random_questions"]}</MenuItem>
                                </Select>
                            </Box>
                        </Tooltip>
                    </Grid>



                    {isBlocking && <Grid size={{ xs: 12 }}>
                        <Box>
                            <InputLabel sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                                {localeMessages["limited_attempts"]}
                            </InputLabel>
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={limitedAttempts}
                                        onChange={(e) => setLimitedAttempts(e.target.checked)}
                                        disabled={userRole === 'viewer'}
                                    />
                                }
                                label={localeMessages["limited_attempts"]}
                            />
                            <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.5 }}>
                                {localeMessages["limited_attempts_tooltip"]}
                            </Typography>
                        </Box>
                    </Grid>}
                </Grid>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', position: 'sticky', bottom: 0, backgroundColor: 'background.paper', py: 2, zIndex: 99 }}>
                <Button variant="outlined" sx={{ mr: 1, boxShadow: 'none' }} onClick={cancel}>
                    {localeMessages["back"]}
                </Button>
                {userRole !== 'viewer' && <Button type="submit" variant="contained" color="secondary" sx={{ boxShadow: 'none', mr: 1}} onClick={() => {if(!quizId) { addQuiz(); } else { updateQuiz(); }}}>
                    {localeMessages["save_quiz"]}
                </Button>}
            </Box>
            <Dialog open={confirmCloseDialogOpen} onClose={() => setConfirmCloseDialogOpen(false)}>
                <Box sx={{ p: 3 }}>
                    <Typography variant="h2" sx={{ fontSize: '1.25rem', mb: 2 }}>{localeMessages["confirm_close"]}</Typography>
                    <Typography sx={{ mb: 3 }}>{localeMessages["unsaved_changes_warning"]}</Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <Button variant="outlined" sx={{ mr: 1 }} onClick={() => setConfirmCloseDialogOpen(false)}>
                            {localeMessages["cancel"]}
                        </Button>
                        <Button variant="contained" color="secondary" onClick={() => {
                            setConfirmCloseDialogOpen(false);
                            cancel();
                        }}>
                            {localeMessages["close_without_saving"]}
                        </Button>
                    </Box>
                </Box>
            </Dialog>
        </Box>
    );
}

export default QuizForm;
