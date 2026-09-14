import render, { useAppContext } from '../../src/render.jsx';
import { useState } from 'react';
import Layout from '../../public/components/Layout.jsx';
import { sanitizeEndpointUrl } from '../../src/sanitizeUrl.js';
import {
	Alert,
	Box,
	Button,
	FormControl,
	FormControlLabel,
	Radio,
	RadioGroup,
	Typography,
} from '@mui/material';


const Decision = () => {
	const {
		localeMessages,
		token,
		csrfToken,
		apiEndpoint: rawApiEndpoint,
		errorMessage,
		decision,
		ref,
		direction,
	} = useAppContext();

	const apiEndpoint = sanitizeEndpointUrl(rawApiEndpoint);

	const [optionId, setOptionId] = useState('');
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [submissionMessage, setSubmissionMessage] = useState('');
	const [formError, setFormError] = useState('');

	const submitAnswer = () => {
		if (!optionId) {
			setFormError(localeMessages.choose_an_answer || 'Choose one answer');
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
			body: JSON.stringify({ token, option_id: Number(optionId) }),
		})
			.then(async (response) => {
				const data = await response.json();
				if (!response.ok) {
					throw new Error(typeof data.error === 'string' ? data.error : localeMessages.submission_error);
				}
				return data;
			})
			.then((data) => {
				setSubmissionMessage(data.message || localeMessages.submission_success || '');
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
					maxWidth: 720,
					mx: 'auto',
					p: { xs: 2, md: 4 },
					borderRadius: 2,
					backgroundColor: 'background.paper',
				}}
				dir={direction}
			>
				{errorMessage ? (
					<Alert severity="error">
						<Typography variant="h6">
							{localeMessages.error}: {errorMessage}{' '}
							{ref && `(Ref: ${ref})`}
						</Typography>
					</Alert>
				) : submissionMessage ? (
					<Box sx={{ textAlign: 'center' }}>
						<Alert severity="success">
							<Typography variant="h6">{submissionMessage}</Typography>
						</Alert>
						<Box sx={{ mt: 5, fontSize: '0.8rem' }}>
							<Typography>{localeMessages.close_window_message}</Typography>
						</Box>
					</Box>
				) : (
					<>
						<Typography variant="h4" sx={{ mb: 2 }}>
							{decision?.title}
						</Typography>
						<Typography sx={{ mb: 3, whiteSpace: 'pre-line' }}>
							{decision?.prompt}
						</Typography>

						{formError && (
							<Alert severity="error" sx={{ mb: 2 }}>
								<Typography>{formError}</Typography>
							</Alert>
						)}

						<FormControl sx={{ width: '100%', mb: 3 }}>
							<RadioGroup
								aria-label={decision?.title}
								value={optionId}
								onChange={(event) => {
									setOptionId(event.target.value);
									setFormError('');
								}}
							>
								{(decision?.options || []).map((option) => (
									<FormControlLabel
										key={option.id}
										value={String(option.id)}
										control={<Radio />}
										label={option.text}
										sx={{ py: 0.5 }}
									/>
								))}
							</RadioGroup>
						</FormControl>

						<Box sx={{ textAlign: 'center' }}>
							<Button
								variant="contained"
								onClick={submitAnswer}
								disabled={isSubmitting}
								sx={{ px: 3, fontSize: '1.1rem' }}
							>
								{localeMessages.submit}
							</Button>
						</Box>
					</>
				)}
			</Box>
		</Layout>
	);
};


export { Decision };

render({ children: <Decision /> });
