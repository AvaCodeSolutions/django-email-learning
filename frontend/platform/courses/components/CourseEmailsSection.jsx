import { Alert, Box, Button, Chip, Divider, FormControlLabel, Radio, RadioGroup, Stack, TextField, Typography } from '@mui/material';
import { useRef } from 'react';
import ContentEditor from '../../../src/components/ContentEditor.jsx';
import { useAppContext } from '../../../src/render.jsx';

const PLACEHOLDERS = ['course_title', 'organization_name'];

const placeholderText = (name) => `{{ ${name} }}`;

/**
 * One editable email: its subject, its body and a way back to the built-in default.
 *
 * `editorKey` remounts the editor, which only reads its content when it is created - so
 * restoring the default, or leaving read-only mode, shows up in it.
 */
function EmailEditor({ title, helperText, subject, body, onChange, onRestoreDefault, readOnly, editorKey, subjectLabel }) {
    const { localeMessages, direction } = useAppContext();
    const editorRef = useRef(null);

    const insertPlaceholder = (name) => {
        editorRef.current?.chain().focus().insertContent(placeholderText(name)).run();
    };

    return (
        <Box sx={{ mt: 2 }}>
            <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="subtitle1">{title}</Typography>
                {!readOnly && (
                    <Button onClick={onRestoreDefault} size="small">
                        {localeMessages['restore_default_email'] || 'Restore default'}
                    </Button>
                )}
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{helperText}</Typography>
            <TextField
                label={subjectLabel}
                fullWidth
                margin="normal"
                value={subject}
                disabled={readOnly}
                onChange={(e) => onChange({ subject: e.target.value })}
                slotProps={{ htmlInput: { maxLength: 200 } }}
                dir={direction}
            />
            <ContentEditor
                key={editorKey}
                initialContent={body}
                contentUpdateCallback={(html) => onChange({ body: html })}
                editorInstanceCallback={(editor) => { editorRef.current = editor; }}
                disabled={readOnly}
                defaultDirection={direction}
                autoFocus={false}
            />
            <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: 'center', flexWrap: 'wrap', rowGap: 1 }}>
                <Typography variant="caption" color="text.secondary">
                    {localeMessages['email_placeholders_help'] || 'Placeholders, filled in as each email is sent:'}
                </Typography>
                {PLACEHOLDERS.map((name) => (
                    <Chip
                        key={name}
                        size="small"
                        variant="outlined"
                        label={placeholderText(name)}
                        onClick={readOnly ? undefined : () => insertPlaceholder(name)}
                        sx={{ fontFamily: 'monospace' }}
                    />
                ))}
            </Stack>
        </Box>
    );
}

/**
 * How a course's enrollments are confirmed, and the emails sent around it.
 *
 * The enrollment email can only be edited while enrollments are gated: a course confirmed
 * by email link sends the built-in verification email, so the link learners need can't be
 * removed from it.
 */
function CourseEmailsSection({ values, onChange, onRestoreDefault, readOnly, gateKeyError, editorVersion }) {
    const { localeMessages, direction } = useAppContext();
    const gated = values.enrollmentConfirmation === 'gate';

    return (
        <Box>
            <Typography variant="subtitle1">{localeMessages['enrollment_confirmation'] || 'Enrollment confirmation'}</Typography>
            <RadioGroup
                value={values.enrollmentConfirmation}
                onChange={(e) => onChange({ enrollmentConfirmation: e.target.value })}
                sx={{ mt: 1 }}
            >
                <FormControlLabel
                    value="link"
                    disabled={readOnly}
                    control={<Radio />}
                    label={(
                        <Box>
                            <Typography variant="body1">{localeMessages['enrollment_confirmation_link'] || 'Email link'}</Typography>
                            <Typography variant="body2" color="text.secondary">
                                {localeMessages['enrollment_confirmation_link_help']
                                    || 'Learners confirm their enrollment by clicking the link in the verification email.'}
                            </Typography>
                        </Box>
                    )}
                    sx={{ alignItems: 'flex-start', mb: 1, '& .MuiRadio-root': { pt: 0.25 } }}
                />
                <FormControlLabel
                    value="gate"
                    disabled={readOnly}
                    control={<Radio />}
                    label={(
                        <Box>
                            <Typography variant="body1">{localeMessages['enrollment_confirmation_gate'] || 'Enrollment gate'}</Typography>
                            <Typography variant="body2" color="text.secondary">
                                {localeMessages['enrollment_confirmation_gate_help']
                                    || 'The enrollment waits until your system unlocks the enrollment gate through the API, for example once a payment clears, or an admin confirms it.'}
                            </Typography>
                        </Box>
                    )}
                    sx={{ alignItems: 'flex-start', '& .MuiRadio-root': { pt: 0.25 } }}
                />
            </RadioGroup>
            {gated && (
                <TextField
                    label={localeMessages['enrollment_gate_key'] || 'Enrollment gate key'}
                    fullWidth
                    margin="normal"
                    required
                    value={values.enrollmentGateKey}
                    disabled={readOnly}
                    onChange={(e) => onChange({ enrollmentGateKey: e.target.value })}
                    error={Boolean(gateKeyError)}
                    helperText={gateKeyError || localeMessages['enrollment_gate_key_help']
                        || 'Name this key in the unlock API call to confirm an enrollment. It must differ from the keys of the gates in the course.'}
                    slotProps={{ htmlInput: { maxLength: 100, style: { fontFamily: 'monospace' } } }}
                    dir="ltr"
                />
            )}
            <Divider sx={{ my: 2 }} />
            {gated ? (
                <EmailEditor
                    title={localeMessages['enrollment_email'] || 'Enrollment email'}
                    helperText={localeMessages['enrollment_email_help']
                        || 'Sent as soon as a learner enrolls. Tell them what their enrollment is waiting for, and add a button to your payment page that carries their enrollment ID. Leave the message empty to send nothing.'}
                    subjectLabel={localeMessages['email_subject'] || 'Subject'}
                    subject={values.enrollmentEmailSubject}
                    body={values.enrollmentEmailBody}
                    onChange={({ subject, body }) => onChange({
                        ...(subject !== undefined && { enrollmentEmailSubject: subject }),
                        ...(body !== undefined && { enrollmentEmailBody: body }),
                    })}
                    onRestoreDefault={() => onRestoreDefault('enrollment')}
                    readOnly={readOnly}
                    editorKey={`enrollment-${editorVersion}-${readOnly}`}
                />
            ) : (
                <Alert severity="info" sx={{ direction }}>
                    {localeMessages['enrollment_email_link_mode_info']
                        || 'Learners receive the built-in verification email with their confirmation link. Switch to an enrollment gate to write your own enrollment email.'}
                </Alert>
            )}
            <Divider sx={{ my: 2 }} />
            <EmailEditor
                title={localeMessages['welcome_email'] || 'Welcome email'}
                helperText={localeMessages['welcome_email_help'] || 'Sent once the enrollment is confirmed, just before the course starts.'}
                subjectLabel={localeMessages['email_subject'] || 'Subject'}
                subject={values.welcomeEmailSubject}
                body={values.welcomeEmailBody}
                onChange={({ subject, body }) => onChange({
                    ...(subject !== undefined && { welcomeEmailSubject: subject }),
                    ...(body !== undefined && { welcomeEmailBody: body }),
                })}
                onRestoreDefault={() => onRestoreDefault('welcome')}
                readOnly={readOnly}
                editorKey={`welcome-${editorVersion}-${readOnly}`}
            />
        </Box>
    );
}

export default CourseEmailsSection;
