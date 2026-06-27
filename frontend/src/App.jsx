import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow.jsx";

function getInitialTheme() {
  // O index.html já definiu data-theme antes do React montar; partimos dele.
  const current = document.documentElement.getAttribute("data-theme");
  if (current === "light" || current === "dark") return current;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("theme", theme);
    } catch (e) {
      /* localStorage indisponível — ignora */
    }
  }, [theme]);

  const isDark = theme === "dark";

  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">INT</span>
          <div className="brand__text">
            <h1 className="app__title">Secretaria de Assuntos Internacionais</h1>
            <p className="app__subtitle">Universidade de Brasília</p>
          </div>
        </div>
        <button
          className="theme-toggle"
          onClick={() => setTheme(isDark ? "light" : "dark")}
          aria-label={isDark ? "Mudar para tema claro" : "Mudar para tema escuro"}
          title={isDark ? "Tema claro" : "Tema escuro"}
        >
          {isDark ? "☀️" : "🌙"}
        </button>
      </header>
      <p className="app__disclaimer">
        Assistente não oficial sobre o site do INT
      </p>
      <ChatWindow />
    </div>
  );
}
