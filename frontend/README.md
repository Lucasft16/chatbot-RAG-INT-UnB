# Frontend — Chatbot INT/UnB

Interface de chat minimalista de uma tela (Vite + React) que conversa com o backend FastAPI.

> Projeto pessoal/acadêmico de portfólio. Não é canal oficial do INT/UnB.

## Recursos

- **Tela única de chat** com histórico, estado vazio (perguntas-exemplo clicáveis), indicador
  de digitação e auto-scroll.
- **Respostas em markdown** (negrito, listas, links, tabelas) via `react-markdown` + `remark-gfm`;
  mensagens do usuário ficam como texto puro.
- **Tema claro/escuro** com botão no cabeçalho, persistido em `localStorage` e respeitando a
  preferência do sistema (sem flash no carregamento).
- **Fontes citadas** sob cada resposta (sem duplicatas), abrindo a página de origem do INT.

## Como rodar

```bash
npm install
cp .env.example .env   # ajuste VITE_API_URL se o backend não estiver em :8000
npm run dev            # http://localhost:5173
```

O backend precisa estar rodando (ver [`../backend/README.md`](../backend/README.md)).

## Stack

| Item | Escolha |
|------|---------|
| Build | Vite |
| UI | React 18 |
| Markdown | react-markdown + remark-gfm |
| Estilo | CSS puro com variáveis (tema claro/escuro), sem framework |

## Estrutura

```
src/
├── components/   # ChatWindow, MessageBubble (markdown), InputBar
├── api/          # chatClient.js (chamadas ao backend)
├── index.css     # estilo único + variáveis de tema (claro/escuro)
├── App.jsx       # cabeçalho + toggle de tema
└── main.jsx
```
