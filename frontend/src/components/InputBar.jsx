// Barra de input: campo de texto + botão de enviar.
// Enter envia; Shift+Enter quebra linha. O campo cresce com o conteúdo.

import { useRef, useState } from "react";

export default function InputBar({ onSend, disabled }) {
  const [value, setValue] = useState("");
  const ref = useRef(null);

  function submit() {
    const q = value.trim();
    if (!q || disabled) return;
    onSend(q);
    setValue("");
    if (ref.current) ref.current.style.height = "auto";
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleInput(e) {
    setValue(e.target.value);
    // Auto-resize: ajusta a altura ao conteúdo.
    e.target.style.height = "auto";
    e.target.style.height = `${e.target.scrollHeight}px`;
  }

  return (
    <div className="input-bar">
      <textarea
        ref={ref}
        className="input-bar__field"
        rows={1}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="Pergunte sobre o INT/UnB…"
        disabled={disabled}
      />
      <button
        type="button"
        className="input-bar__send"
        onClick={submit}
        disabled={disabled || !value.trim()}
      >
        Enviar
      </button>
    </div>
  );
}
