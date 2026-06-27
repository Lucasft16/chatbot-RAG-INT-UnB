// Janela de chat: histórico de mensagens + barra de input.

import { useEffect, useRef, useState } from "react";
import { sendQuestion } from "../api/chatClient.js";
import InputBar from "./InputBar.jsx";
import MessageBubble from "./MessageBubble.jsx";

const EXAMPLES = [
  "Como funciona o intercâmbio de graduação?",
  "Quais seleções estão abertas no momento?",
  "Como entro em contato com o INT?",
];

export default function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  // Rola para a última mensagem sempre que o histórico muda.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(question) {
    setMessages((m) => [...m, { role: "user", text: question }]);
    setLoading(true);
    try {
      const { answer, sources } = await sendQuestion(question);
      setMessages((m) => [...m, { role: "bot", text: answer, sources }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "bot", text: err.message, isError: true }]);
    } finally {
      setLoading(false);
    }
  }

  const isEmpty = messages.length === 0 && !loading;

  return (
    <>
      <div className="messages">
        {isEmpty ? (
          <div className="empty">
            <p className="empty__title">Pergunte algo sobre o site do INT/UnB.</p>
            <div className="empty__examples">
              {EXAMPLES.map((q) => (
                <button
                  key={q}
                  className="empty__example"
                  onClick={() => handleSend(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m, i) => (
              <MessageBubble key={i} {...m} />
            ))}
            {loading && <MessageBubble role="bot" typing />}
          </>
        )}
        <div ref={endRef} />
      </div>
      <InputBar onSend={handleSend} disabled={loading} />
    </>
  );
}
