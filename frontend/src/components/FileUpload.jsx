import { useState } from 'react';
import { styled } from '@mui/material/styles';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';


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


const FileUpload = ({
    uploadApiEndpoint,
    token,
    csrfToken,
    direction = 'ltr',
    uploadLabel = 'Upload File',
    removeLabel = 'Remove File',
    helperText = '',
    onUploadSuccess,
    onUploadError,
}) => {
    const [isUploading, setIsUploading] = useState(false);
    const [uploadedFileName, setUploadedFileName] = useState('');
    const [uploadError, setUploadError] = useState('');

    const uploadFile = (selectedFile) => {
        if (!selectedFile || !uploadApiEndpoint) {
            return;
        }

        setIsUploading(true);
        setUploadError('');

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('token', token);

        fetch(uploadApiEndpoint, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            body: formData,
        })
            .then(async (response) => {
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'File upload failed.');
                }
                return data;
            })
            .then((data) => {
                setUploadedFileName(data.file_name || selectedFile.name);
                if (onUploadSuccess) {
                    onUploadSuccess(data);
                }
            })
            .catch((error) => {
                setUploadError(error.message || 'File upload failed.');
                if (onUploadError) {
                    onUploadError(error);
                }
            })
            .finally(() => {
                setIsUploading(false);
            });
    };

    const clearUploadedFile = () => {
        setUploadedFileName('');
        setUploadError('');
        if (onUploadSuccess) {
            onUploadSuccess({ file_path: null, file_name: null });
        }
    };

    const handleFileChange = (event) => {
        const selectedFile = event.target.files?.[0];
        if (!selectedFile) {
            return;
        }
        uploadFile(selectedFile);
        event.target.value = '';
    };

    return (
        <Box>
            <Button
                component="label"
                role={undefined}
                variant="outlined"
                tabIndex={-1}
                startIcon={<CloudUploadIcon sx={{ marginLeft: direction === 'rtl' ? 1 : 0 }} />}
                disabled={isUploading}
                sx={{ textAlign: direction === 'rtl' ? 'right' : 'left' }}
                dir={direction}
            >
                {isUploading ? 'Uploading...' : uploadLabel}
                <VisuallyHiddenInput type="file" onChange={handleFileChange} />
            </Button>

            {helperText && (
                <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                    {helperText}
                </Typography>
            )}

            {uploadedFileName && (
                <Box sx={{ mt: 1.5 }}>
                    <Typography sx={{ color: 'text.secondary' }}>{uploadedFileName}</Typography>
                    <Button variant="text" onClick={clearUploadedFile} sx={{ px: 0, mt: 0.5 }}>
                        {removeLabel}
                    </Button>
                </Box>
            )}

            {uploadError && (
                <Alert severity="error" sx={{ mt: 1.5 }}>
                    <Typography>{uploadError}</Typography>
                </Alert>
            )}
        </Box>
    );
};


export default FileUpload;
