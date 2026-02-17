import { StrictMode, createContext, useContext, useMemo } from "react";
import { createRoot } from "react-dom/client";
import { ThemeContextProvider } from "./theme/ThemeContext";
import { lightTheme, darkTheme } from "./theme/themes";


const AppContext = createContext(null);

export const useAppContext = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used inside render()");
  return ctx;
};

function readDjangoContext() {
  const el = document.getElementById("app-context");
  if (!el?.textContent) return {};
  try {
    return JSON.parse(el.textContent);
  } catch {
    return {};
  }
}

function render({ children }) {
  const djangoCtx = readDjangoContext();
  const appContext = {
    direction: "ltr",
    ...djangoCtx,
  };

  let storedTheme = localStorage.getItem("theme");
  if (!storedTheme) {
    localStorage.setItem("theme", "light");
    storedTheme = "light";
  }
  const initialTheme = storedTheme === "dark" ? darkTheme : lightTheme;
  console.log(appContext);
  createRoot(document.getElementById("root")).render(
    <StrictMode>
      <ThemeContextProvider initialTheme={initialTheme}>
        <AppContext.Provider value={appContext}>{children}</AppContext.Provider>
      </ThemeContextProvider>
    </StrictMode>
  );
}

export default render;
