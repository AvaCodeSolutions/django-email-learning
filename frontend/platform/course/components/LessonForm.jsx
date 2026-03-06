import { useState, useEffect, use } from 'react';
import { Alert, Box, Button, Typography, Select, MenuItem, Tooltip, Link, IconButton, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions } from '@mui/material';
import { styled } from '@mui/material/styles';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import RequiredTextField from '../../../src/components/RequiredTextField.jsx';
import ContentEditor from '../../../src/components/ContentEditor.jsx';
import { getCookie } from '../../../src/utils.js';
import { useAppContext } from '../../../src/render.jsx';

function LessonForm({ header, initialTitle, initialContent, cancelCallback, successCallback, courseId, lessonId, initialWaitingPeriod, contentId }) {
    const [title, setTitle] = useState(initialTitle || "");
    const [content, setContent] = useState(initialContent || "");
    const [waitingPeriod, setWaitingPeriod] = useState(initialWaitingPeriod ? initialWaitingPeriod.period : 1);
    const [waitingPeriodUnit, setWaitingPeriodUnit] = useState(initialWaitingPeriod ? initialWaitingPeriod.type : "days");
    const [titleHelperText, setTitleHelperText] = useState("");
    const [contentHelperText, setContentHelperText] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [uploadedImages, setUploadedImages] = useState([]);
    const [imageUploadError, setImageUploadError] = useState("");
    const [editorInstance, setEditorInstance] = useState(null);
    const [imagePendingDelete, setImagePendingDelete] = useState(null);
    const [deleteImageDialogOpen, setDeleteImageDialogOpen] = useState(false);
    const [isDeletingImage, setIsDeletingImage] = useState(false);


    const { localeMessages, apiBaseUrl, userRole, direction } = useAppContext();
    const orgId = localStorage.getItem('activeOrganizationId');

    const VisuallyHiddenInput = styled('input')({
        clip: 'rect(0 0 0 0)',
        clipPath: 'inset(50%)',
        height: 1,
        overflow: 'hidden',
        position: 'absolute',
        bottom: 0,
        left: 0,
        whiteSpace: 'nowrap',
        width: 1,
    });


    const addLesson = () =>{
        if (!validateForm()) {
            setErrorMessage(localeMessages["fix_errors"]);
            return;
        }

        console.log("Adding lesson to course ID:", courseId);
        fetch(apiBaseUrl + '/organizations/' + orgId + '/courses/' + courseId + '/contents/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                content: {
                    title: title,
                    content: content,
                    type: 'lesson'
                },
                waiting_period: {"period": waitingPeriod, "type": waitingPeriodUnit},
            }),
        })
        .then((response) => response.json())
        .then((data) => {
            console.log('Lesson created successfully:', data);
            setContent("");
            setTitle("");
            successCallback();
        })
        .catch((error) => {
            console.error('Error creating lesson:', error);
        });
    }

    const updateLesson = () => {
        if (!validateForm()) {
            setErrorMessage(localeMessages["fix_errors"]);
            return;
        }

        console.log("Updating lesson ID:", lessonId);

        fetch(apiBaseUrl + '/organizations/' + orgId + '/courses/' + courseId + '/contents/' + contentId + '/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                lesson: {
                    title: title,
                    content: content,
                },
                waiting_period: {"period": waitingPeriod, "type": waitingPeriodUnit},
            }),
        })
        .then((response) => {
            console.log(response)
            if (response.status === 200) {
                console.log('Lesson updated successfully');
                successCallback();
            }
        })
        .catch((error) => {
            console.error('Error updating lesson:', error);
        });
    }

    const handleContentChange = (newContent) => {
        setContent(newContent);
    }

    const cancel = () => {
        setContent("");
        setTitle("");
        cancelCallback();
    }

    const validateForm = () => {
        let isValid = true;
        if (!title) {
            setTitleHelperText(localeMessages["lesson_title_required"]);
            isValid = false;
        } else {
            setTitleHelperText("");
        }
        if (!content) {
            setContentHelperText(localeMessages["lesson_content_required"]);
            isValid = false;
        } else {
            setContentHelperText("");
        }
        return isValid;
    }

    const handleLessonImageUpload = (event) => {
        const selectedFile = event.target.files?.[0];
        if (!selectedFile) {
            return;
        }

        const isImage = selectedFile.type.startsWith('image/');
        const isWebp = selectedFile.type === 'image/webp' || selectedFile.name.toLowerCase().endsWith('.webp');

        if (!isImage || isWebp) {
            setImageUploadError('Only non-WebP image files are allowed.');
            event.target.value = '';
            return;
        }

        setImageUploadError('');

        const formData = new FormData();
        formData.append('file', selectedFile);

        fetch(`${apiBaseUrl}/organizations/${orgId}/file/`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData,
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error('Image upload failed');
                }
                return response.json();
            })
            .then((data) => {
                setUploadedImages((previousImages) => [...previousImages, data]);
                event.target.value = '';
            })
            .catch((error) => {
                console.error('Error uploading lesson image:', error);
                setImageUploadError('Image upload failed. Please try again.');
            });
    }

    const removeUploadedImageFromList = (imageUrl) => {
        setUploadedImages((previousImages) => previousImages.filter((image) => image.file_url !== imageUrl));
    }

    const normalizeUrlForComparison = (url) => {
        if (!url) {
            return "";
        }

        try {
            const parsedUrl = new URL(url, window.location.origin);
            return `${parsedUrl.origin}${parsedUrl.pathname}`.toLowerCase();
        } catch {
            return String(url).trim().toLowerCase();
        }
    }

    const isImageUsedInEditor = (imageUrl) => {
        const currentEditorContent = editorInstance?.getHTML?.() || content || "";
        if (!currentEditorContent) {
            return false;
        }

        const targetImageUrl = normalizeUrlForComparison(imageUrl);
        if (!targetImageUrl) {
            return false;
        }

        try {
            const parser = new DOMParser();
            const editorDocument = parser.parseFromString(currentEditorContent, 'text/html');
            const imageSources = Array.from(editorDocument.querySelectorAll('img'))
                .map((imageElement) => normalizeUrlForComparison(imageElement.getAttribute('src')))
                .filter(Boolean);

            return imageSources.includes(targetImageUrl);
        } catch {
            return currentEditorContent.includes(imageUrl);
        }
    }

    const requestRemoveUploadedImage = (image) => {
        if (!image?.file_url) {
            return;
        }

        if (isImageUsedInEditor(image.file_url)) {
            setImageUploadError(localeMessages["uploaded_image_used_in_editor_error"]);
            return;
        }

        setImageUploadError('');
        setImagePendingDelete(image);
        setDeleteImageDialogOpen(true);
    }

    const confirmRemoveUploadedImage = () => {
        if (!imagePendingDelete?.file_path) {
            setDeleteImageDialogOpen(false);
            setImagePendingDelete(null);
            setImageUploadError(localeMessages["uploaded_image_delete_failed"]);
            return;
        }

        setIsDeletingImage(true);
        fetch(`${apiBaseUrl}/organizations/${orgId}/file/`, {
            method: 'DELETE',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                file_path: imagePendingDelete.file_path,
                file_url: imagePendingDelete.file_url,
            }),
        })
            .then(async (response) => {
                if (!response.ok) {
                    throw new Error('Image delete failed');
                }
                removeUploadedImageFromList(imagePendingDelete.file_url);
                setDeleteImageDialogOpen(false);
                setImagePendingDelete(null);
                setImageUploadError('');
            })
            .catch((error) => {
                console.error('Error deleting lesson image:', error);
                setImageUploadError(localeMessages["uploaded_image_delete_failed"]);
            })
            .finally(() => {
                setIsDeletingImage(false);
            });
    }

    const addImageToEditor = (imageUrl) => {
        if (!editorInstance || !imageUrl) {
            return;
        }
        editorInstance.chain().focus().setImage({ src: imageUrl }).run();
    }

    return (
        <>
        <Box sx={{ p: 3 }}>
        <Typography variant="h2" sx={{ my: 2, fontSize: '1.5rem' }}>{header}</Typography>
        { errorMessage && (
            <Alert severity="error" sx={{ marginBottom: "10px" }}>
                {errorMessage}
            </Alert>
        )}
        <RequiredTextField value={title} label={localeMessages["lesson_title"]} name="lesson_title" sx={{ width: '100%' }} onChange={(e) => setTitle(e.target.value)} helperText={titleHelperText} disabled={userRole === 'viewer'} />
        <Box sx={{ my: 2 }}>
        <ContentEditor initialContent={content} contentUpdateCallback={handleContentChange} disabled={userRole === 'viewer'} extraMinLines={3} editorInstanceCallback={setEditorInstance} defaultDirection={direction} />
        <Typography color="errorText.main" sx={{ marginTop: 1, fontSize: '0.75rem' }}>
            {contentHelperText}
        </Typography>
        </Box>
        <Box sx={{ my: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>{localeMessages["upload_images"] || "Upload Images"}</Typography>
            {imageUploadError && (
                <Alert severity="error" sx={{ mb: 1 }}>
                    {imageUploadError}
                </Alert>
            )}
            {userRole !== 'viewer' && (
                <Button component="label" variant="outlined" sx={{ mb: 1.5 }}>
                    {localeMessages["upload"]}
                    <VisuallyHiddenInput
                        type="file"
                        accept="image/png,image/jpeg,image/gif,image/bmp,image/svg+xml,image/tiff,image/avif"
                        onChange={handleLessonImageUpload}
                    />
                </Button>
            )}
            <Box sx={{ border: '1px solid', borderColor: 'border.main', borderRadius: 1, p: 1.25, backgroundColor: 'background.box' }}>
                {uploadedImages.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">{localeMessages["no_uploaded_images"] || "No uploaded images yet."}</Typography>
                ) : (
                    uploadedImages.map((image, index) => (
                        <Box key={`${image.file_url}-${index}`} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 0.5, gap: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, flex: 1 }}>
                                <Box
                                    component="img"
                                    src={image.file_url}
                                    alt={localeMessages["uploaded_image_preview"]}
                                    sx={{
                                        width: 47,
                                        height: 47,
                                        borderRadius: 0.5,
                                        objectFit: 'contain',
                                        border: '1px solid',
                                        borderColor: 'border.main',
                                        flexShrink: 0,
                                    }}
                                />
                                <Link href={image.file_url} target="_blank" rel="noopener noreferrer" sx={{ wordBreak: 'break-all', minWidth: 0 }}>
                                    {image.file_url}
                                </Link>
                            </Box>
                            {userRole !== 'viewer' && (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
                                    <IconButton aria-label={localeMessages["add_image_to_editor"]} onClick={() => addImageToEditor(image.file_url)} size="small">
                                        <AddIcon fontSize="small" />
                                    </IconButton>
                                    <IconButton aria-label={localeMessages["remove_uploaded_image"]} onClick={() => requestRemoveUploadedImage(image)} size="small">
                                        <DeleteIcon fontSize="small" />
                                    </IconButton>
                                </Box>
                            )}
                        </Box>
                    ))
                )}
            </Box>
        </Box>
        <Tooltip
        placement="right"
        title={localeMessages["lesson_waiting_tooltip"]}>
        <RequiredTextField
            label={localeMessages["waiting_period"]}
            name="waiting_period"
            type="number"
            value={waitingPeriod}
            onChange={(e) => setWaitingPeriod(e.target.value)}
            sx={{ width: '200px', mr: 2 }}
            inputProps={{ min: 1 }}
            disabled={userRole === 'viewer'}
        />
        <Select size="small" value={waitingPeriodUnit} onChange={(e) => setWaitingPeriodUnit(e.target.value)} name="waiting_period_unit" sx={{ width: '150px', mr: 2 }} disabled={userRole === 'viewer'}>
            <MenuItem value="days">{localeMessages["days"]}</MenuItem>
            <MenuItem value="hours">{localeMessages["hours"]}</MenuItem>
        </Select>
        </Tooltip>
        <Box mt={2} textAlign="right">
        <Button variant="outlined" sx={{ mr: 1 }} onClick={cancel}>
            {localeMessages["back"]}
        </Button>
        {userRole !== 'viewer' && <Button type="submit" variant="contained" sx={{ mr: 1 }} onClick={() => {if(!lessonId) { addLesson(); } else { updateLesson(); }}}>
            {localeMessages["save_lesson"]}
        </Button>}
        </Box>
        </Box>
        <Dialog
            open={deleteImageDialogOpen}
            onClose={() => {
                if (isDeletingImage) {
                    return;
                }
                setDeleteImageDialogOpen(false);
                setImagePendingDelete(null);
            }}
            maxWidth="sm"
            fullWidth
        >
            <DialogTitle>{localeMessages["confirm_delete_uploaded_image"]}</DialogTitle>
            <DialogContent>
                <DialogContentText>
                    {localeMessages["delete_uploaded_image_warning"]}
                </DialogContentText>
                {imagePendingDelete?.file_url && (
                    <Typography variant="body2" sx={{ mt: 1, wordBreak: 'break-all' }}>
                        {imagePendingDelete.file_url}
                    </Typography>
                )}
            </DialogContent>
            <DialogActions>
                <Button
                    onClick={() => {
                        setDeleteImageDialogOpen(false);
                        setImagePendingDelete(null);
                    }}
                    disabled={isDeletingImage}
                >
                    {localeMessages["cancel"]}
                </Button>
                <Button onClick={confirmRemoveUploadedImage} color="error" disabled={isDeletingImage}>
                    {localeMessages["delete"]}
                </Button>
            </DialogActions>
        </Dialog>
        </>
    );
}

export default LessonForm;
