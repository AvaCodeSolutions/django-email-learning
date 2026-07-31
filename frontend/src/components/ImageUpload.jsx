import { useState, useEffect } from 'react';
import { styled } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import BusinessIcon from '@mui/icons-material/Business';
import { getCookie } from '../utils.js';
import { useAppContext } from '../render.jsx';
import { sanitizeEndpointUrl, sanitizeImageUrl } from '../sanitizeUrl.js';

const AVATAR_SIZE = 96;

const ImageUpload = ({ onUploadSuccess, onUploadError, initialUrl, organizationId, disabled = false, altText, variant = 'button' }) => {
    console.log("Rendering ImageUpload component with initialUrl:", initialUrl);
    const [imageFile, setImageFile] = useState(null);
    const [imageUrl, setImageUrl] = useState(initialUrl);
    const { localeMessages, direction, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const safeImageUrl = sanitizeImageUrl(imageUrl);


    useEffect(() => {
        setImageUrl(initialUrl);
    }, [initialUrl]);

    const removeImage = () => {
        setImageUrl(null);
        setImageFile(null);
        onUploadSuccess({ file_url: null, file_path: null });
    }

    useEffect(() => {
        if (imageFile) {
            fetch(`${apiBaseUrl}/organizations/${organizationId}/files/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: (() => {
                    const formData = new FormData();
                    formData.append('file', imageFile);
                    return formData;
                })(),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('File upload failed');
                }
                return response.json();
            })
            .then(data => {
                console.log('File uploaded successfully:', data);
                onUploadSuccess(data);
                setImageUrl(data.file_url);
            })
            .catch(error => {
                console.error('Error uploading file:', error);
                onUploadError(error);
            });
        }
    }, [imageFile]);

    const handleFileChange = (event) => {
        const selectedFile = event.target.files?.[0];
        if (!selectedFile) {
            return;
        }

        const isImage = selectedFile.type.startsWith('image/');
        const isWebp = selectedFile.type === 'image/webp' || selectedFile.name.toLowerCase().endsWith('.webp');

        if (!isImage || isWebp) {
            event.target.value = '';
            if (onUploadError) {
                onUploadError(new Error('Only non-WebP image files are allowed.'));
            }
            return;
        }

        setImageFile(selectedFile);
    }

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

    if (variant === 'avatar') {
        return (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                <Box sx={{ position: 'relative', width: AVATAR_SIZE, height: AVATAR_SIZE }}>
                    <Avatar
                        src={safeImageUrl}
                        alt={altText || localeMessages["uploaded_image_alt"]}
                        sx={{ width: AVATAR_SIZE, height: AVATAR_SIZE, bgcolor: 'action.hover', color: 'text.secondary' }}
                    >
                        {!safeImageUrl && <BusinessIcon sx={{ fontSize: AVATAR_SIZE * 0.45 }} />}
                    </Avatar>
                    {!disabled && (
                        <IconButton
                            component="label"
                            size="small"
                            aria-label={localeMessages["upload_button_label"]}
                            sx={{
                                position: 'absolute',
                                bottom: 0,
                                insetInlineEnd: 0,
                                bgcolor: 'background.paper',
                                border: '1px solid',
                                borderColor: 'divider',
                                '&:hover': { bgcolor: 'background.paper' },
                            }}
                        >
                            <CloudUploadIcon fontSize="small" />
                            <VisuallyHiddenInput
                                type="file"
                                accept="image/png,image/jpeg,image/gif,image/bmp,image/svg+xml,image/tiff,image/avif"
                                onChange={handleFileChange}
                            />
                        </IconButton>
                    )}
                </Box>
                {safeImageUrl && !disabled ? (
                    <Button variant="text" color="primary" size="small" onClick={removeImage}>{localeMessages["remove_image"]}</Button>
                ) : !safeImageUrl && (
                    <Typography variant="caption" color="text.secondary">{altText || localeMessages["uploaded_image_alt"]}</Typography>
                )}
            </Box>
        );
    }

    return (<>
        { !safeImageUrl ? <Button
            component="label"
            role={undefined}
            variant="contained"
            tabIndex={-1}
            disabled={disabled}
            startIcon={<CloudUploadIcon sx={{ marginLeft: direction === 'rtl' ? 1 : 0 }} />}
            sx={{ textAlign: direction === 'rtl' ? 'right' : 'left', mt: 2, mb: 2}}
            dir={direction}
            >
            {localeMessages["upload_button_label"]}
            <VisuallyHiddenInput
                type="file"
                accept="image/png,image/jpeg,image/gif,image/bmp,image/svg+xml,image/tiff,image/avif"
                onChange={handleFileChange}
                disabled={disabled}
            />
            </Button>
            : (<><img src={safeImageUrl} alt={altText || localeMessages["uploaded_image_alt"]} style={{ marginTop: '10px', maxHeight: '100px' }} /><br />
                <Button variant="text" color="primary" onClick={removeImage} disabled={disabled}>{localeMessages["remove_image"]}</Button></>
            )}
    </>)
}

export default ImageUpload;
