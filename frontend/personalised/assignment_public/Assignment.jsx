import render, { useAppContext } from '../../src/render.jsx';
import { useState } from 'react';
import Layout from '../../public/components/Layout.jsx';
import FileUpload from '../../src/components/FileUpload.jsx';
import {
	Alert,
	Box,
	Button,
	TextField,
	Typography,
} from '@mui/material';


const Assignment = () => {
	const {
		localeMessages,
		token,
		csrfToken,
		apiEndpoint,
		fileUploadApiEndpoint,
		errorMessage,
		assignment,
		ref,
		direction,
	} = useAppContext();

	const [textSubmission, setTextSubmission] = useState('');
	const [filePath, setFilePath] = useState('');
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [submissionSuccess, setSubmissionSuccess] = useState(false);
	const [submissionMessage, setSubmissionMessage] = useState('');
	const [formError, setFormError] = useState('');

	const requiresTextSubmission = Boolean(assignment?.requires_text_submission);
	const requiresFileSubmission = Boolean(assignment?.requires_file_submission);

	const validateSubmission = () => {
		if (requiresTextSubmission && !textSubmission.trim()) {
			return localeMessages.text_submission_required || 'Text submission is required.';
		}
		if (requiresFileSubmission && !filePath) {
			return localeMessages.file_submission_required || 'File submission is required.';
		}
		return '';
	};

	const submitAssignment = () => {
		const validationError = validateSubmission();
		if (validationError) {
			setFormError(validationError);
			return;
		}

		setIsSubmitting(true);
		setFormError('');

		fetch(`${apiEndpoint}`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken,
			},
			body: JSON.stringify({
				token,
				text_submission: textSubmission.trim() || null,
				file_path: filePath || null,
			}),
		})
			.then(async (response) => {
				const data = await response.json();
				if (!response.ok) {
					throw new Error(data.error || localeMessages.submission_error);
				}
				return data;
			})
			.then((data) => {
				setSubmissionSuccess(true);
				setSubmissionMessage(
					data.message || localeMessages.submission_success
				);
			})
			.catch((error) => {
				setFormError(error.message || localeMessages.submission_error);
			})
			.finally(() => {
				setIsSubmitting(false);
			});
	};

	return (
		<Layout>
			<Box
				sx={{
					width: '100%',
					maxWidth: 920,
					mx: 'auto',
					p: { xs: 2, md: 4 },
					borderRadius: 2,
					backgroundColor: 'background.paper',
				}}
				dir={direction}
			>
				{!errorMessage ? (
					<Box>
						{!submissionSuccess ? (
							<>
								<Box sx={{ mb: 3 }}>
									<Typography variant="h4" sx={{ mb: 1 }}>
										{assignment?.title}
									</Typography>
									{assignment?.description && (
										<Typography sx={{ color: 'text.secondary' }}>
											{assignment.description}
										</Typography>
									)}
								</Box>

								{formError && (
									<Alert severity="error" sx={{ mb: 2 }}>
										<Typography>{formError}</Typography>
									</Alert>
								)}

								{requiresTextSubmission && (
									<TextField
										multiline
										minRows={8}
										fullWidth
										label={
											localeMessages.text_submission_label ||
											'Your Answer'
										}
										value={textSubmission}
										onChange={(event) =>
											setTextSubmission(event.target.value)
										}
										sx={{ mb: 3 }}
									/>
								)}

								{requiresFileSubmission && (
									<Box sx={{ mb: 3 }}>
										<Typography sx={{ mb: 1 }}>
											{localeMessages.file_submission_label ||
												'Upload Your File'}
										</Typography>
										<FileUpload
											uploadApiEndpoint={fileUploadApiEndpoint}
											token={token}
											csrfToken={csrfToken}
											direction={direction}
											uploadLabel={
												localeMessages.file_submission_label ||
												'Upload Your File'
											}
											removeLabel={localeMessages.remove_file || 'Remove File'}
											helperText={
												localeMessages.upload_before_submit ||
												'Upload your file first, then submit the form.'
											}
											onUploadSuccess={(data) => {
												setFilePath(data.file_path || '');
												setFormError('');
											}}
											onUploadError={(error) => {
												setFormError(
													error?.message || localeMessages.submission_error
												);
											}}
										/>
									</Box>
								)}

								<Box sx={{ mt: 2, textAlign: 'center' }}>
									<Button
										variant="contained"
										onClick={submitAssignment}
										disabled={isSubmitting}
										sx={{ px: 3, fontSize: '1.1rem' }}
									>
										{localeMessages.submit}
									</Button>
								</Box>
							</>
						) : (
							<Box sx={{ textAlign: 'center' }}>
								<Alert severity="success">
									<Typography variant="h6">
										{submissionMessage}
									</Typography>
								</Alert>
								<Box sx={{ mt: 5, fontSize: '0.8rem' }}>
									<Typography>
										{localeMessages.close_window_message}
									</Typography>
								</Box>
							</Box>
						)}
					</Box>
				) : (
					<Alert severity="error">
						<Typography variant="h6">
							{localeMessages.error}: {errorMessage}{' '}
							{ref && `(Ref: ${ref})`}
						</Typography>
					</Alert>
				)}
			</Box>
		</Layout>
	);
};


export { Assignment };

render({ children: <Assignment /> });
