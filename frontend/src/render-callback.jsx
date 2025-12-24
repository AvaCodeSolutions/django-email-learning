import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeProvider } from '@mui/material/styles';
import { lightTheme, darkTheme } from './theme/themes';
import './index.css'

function render({children}) {
    const [currentTheme, setCurrentTheme] = useState(lightTheme);

    // Clone children and pass theme setter as prop
    const childrenWithProps = React.cloneElement(children, {
        onThemeChange: setCurrentTheme,
        availableThemes: { lightTheme, darkTheme }
    });

    createRoot(document.getElementById('root')).render(
        <StrictMode>
            <ThemeProvider theme={currentTheme}>
                {childrenWithProps}
            </ThemeProvider>
        </StrictMode>,
    )
}

export default render;
