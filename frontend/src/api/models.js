import { request } from './client.js'

/**
 * Obtiene el catálogo de modelos disponibles para el proveedor indicado
 * ('chatgpt' | 'api-key'), usando 'api-key' por defecto.
 */
export const listModels = (provider = 'api-key', signal) =>
  request(`/models?provider=${encodeURIComponent(provider)}`, { signal })
