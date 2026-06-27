// Cliente da API de chat do backend (FastAPI).
// Mantém a comunicação com o backend isolada aqui.

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const CONNECTION_ERROR =
  "Não consegui me conectar ao servidor. Verifique se o backend está rodando e tente novamente.";

/**
 * Envia uma pergunta ao backend e retorna { answer, sources }.
 * Lança Error com mensagem amigável se não houver conexão ou o servidor falhar.
 * @param {string} question
 * @returns {Promise<{answer: string, sources: {url: string, title?: string}[]}>}
 */
export async function sendQuestion(question) {
  let res;
  try {
    res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
  } catch {
    // fetch só rejeita quando nem chegou a ter resposta: backend fora do ar,
    // rede indisponível ou bloqueio de CORS.
    throw new Error(CONNECTION_ERROR);
  }

  if (!res.ok) {
    throw new Error(
      `O servidor respondeu com um erro (${res.status}). Tente novamente em instantes.`,
    );
  }
  return res.json();
}
