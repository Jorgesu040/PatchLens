const BASE_URL = '/api'

/** Petición JSON al backend. Lanza un Error si la respuesta no es 2xx. */
export async function request(path, { body, signal, method = 'GET' } = {}) {
  const isForm = body instanceof FormData
  const headers = { Accept: 'application/json' }
  if (body && !isForm) headers['Content-Type'] = 'application/json'

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    signal,
    headers,
    body: isForm || !body ? body : JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Error ${response.status} en ${method} ${path}`)
  }
  return response.json()
}
