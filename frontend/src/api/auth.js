import { request } from './client.js'

/** Estado actual de autenticación (sesión OAuth de ChatGPT y API Key). */
export const getAuthStatus = (signal) => request('/auth/status', { signal })

/** Inicia el flujo OAuth PKCE de ChatGPT (AI.py login). */
export const loginChatGPT = () => request('/auth/chatgpt/login', { method: 'POST' })

/** Cierra y revoca la sesión OAuth de ChatGPT (AI.py logout). */
export const logoutChatGPT = () => request('/auth/chatgpt/logout', { method: 'POST' })

/** Configura la OPENAI_API_KEY en el backend para el proveedor api-key. */
export const setApiKey = (apiKey) =>
  request('/auth/api-key', { method: 'PUT', body: { apiKey } })

/** Elimina la OPENAI_API_KEY configurada en el backend. */
export const clearApiKey = () => request('/auth/api-key', { method: 'DELETE' })
