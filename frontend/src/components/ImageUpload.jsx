import { useState, useEffect } from 'react';
import { styled } from '@mui/material/styles';
import Button from '@mui/material/Button';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { getCookie } from '../utils.js';
import { useAppContext } from '../render.jsx';


const ImageUpload = ({ onUploadSuccess, onUploadError, initialUrl }) => {
    console.log("Rendering ImageUpload component with initialUrl:", initialUrl);
    const [imageFile, setImageFile] = useState(null);
    const [imageUrl, setImageUrl] = useState(initialUrl);
    const { localeMessages, direction, apiBaseUrl } = useAppContext();


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
            fetch(`${apiBaseUrl}/organizations/1/file/`, {
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

    return (<>
        { !imageUrl ? <Button
            component="label"
            role={undefined}
            variant="contained"
            tabIndex={-1}
            startIcon={<CloudUploadIcon sx={{ marginLeft: direction === 'rtl' ? 1 : 0 }} />}
            sx={{ textAlign: direction === 'rtl' ? 'right' : 'left', mt: 2, mb: 2}}
            dir={direction}
            >
            {localeMessages["upload_button_label"]}
            <VisuallyHiddenInput
                type="file"
                onChange={(event) => setImageFile(event.target.files[0])}
            />
            </Button>
            : (<><img src={imageUrl} alt={localeMessages["uploaded_image_alt"]} style={{ marginTop: '10px', maxHeight: '100px' }} /><br />
                <Button variant="text" color="secondary" onClick={removeImage}>{localeMessages["remove_image"]}</Button></>
            )}
    </>)
}

export default ImageUpload;
