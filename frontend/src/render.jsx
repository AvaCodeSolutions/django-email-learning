import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeContextProvider } from './theme/ThemeContext';
import { lightTheme, darkTheme } from './theme/themes';
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';


import './index.css'


function render({children}) {
    let storedTheme = localStorage.getItem('theme');
    if (!storedTheme) {
        localStorage.setItem('theme', 'light');
        storedTheme = 'light';
    }
    const initialTheme = storedTheme === 'dark' ? darkTheme : lightTheme;

    createRoot(document.getElementById('root')).render(
        <StrictMode>
            <ThemeContextProvider initialTheme={initialTheme}>
                {children}
            </ThemeContextProvider>
        </StrictMode>,
    )
}

export default render;
