// Bolha de mensagem (usuário ou bot). Mostra fontes quando presentes.
// Respostas do bot vêm em markdown (negrito, listas, links) e são renderizadas
// como tal; mensagens do usuário ficam como texto puro.

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Links do markdown abrem em nova aba.
const markdownComponents = {
  a: ({ node, ...props }) => <a target="_blank" rel="noreferrer" {...props} />,
};

export default function MessageBubble({ role, text, sources = [], typing = false, isError = false }) {
  const isUser = role === "user";
  const variant = isUser ? "user" : isError ? "error" : "bot";
  return (
    <div className={`bubble-row bubble-row--${isUser ? "user" : "bot"}`}>
      <div className={`bubble bubble--${variant}`}>
        {typing ? (
          <span className="typing" aria-label="digitando">
            <span />
            <span />
            <span />
          </span>
        ) : isUser || isError ? (
          text
        ) : (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {text}
            </ReactMarkdown>
          </div>
        )}
        {sources.length > 0 && (
          <div className="sources">
            <span className="sources__label">Fontes</span>
            {sources.map((s, i) => (
              <a key={i} href={s.url} target="_blank" rel="noreferrer">
                {s.title ?? s.url}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
