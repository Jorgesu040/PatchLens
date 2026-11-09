import { request } from './client.js'

export const listAnalyses = (signal) => request('/analyses', { signal })

export function createAnalysis({
  oldFile,
  newFile,
  projectName,
  engines,
  provider,
  model,
  maxIterations,
  timeout,
}) {
  const form = new FormData()
  form.append('old', oldFile)
  form.append('new', newFile)
  if (projectName) form.append('project_name', projectName)
  engines.forEach((engine) => form.append('engines', engine))
  if (provider) form.append('provider', provider)
  if (model) form.append('model', model)
  if (maxIterations) form.append('max_iterations', String(maxIterations))
  if (timeout) form.append('timeout', String(timeout))
  return request('/analyses', { method: 'POST', body: form })
}

export const getReport = (id, signal) => request(`/analyses/${id}/report`, { signal })

export const getTraces = (id, signal) => request(`/analyses/${id}/traces`, { signal })

export const sendMessage = (id, text) =>
  request(`/analyses/${id}/chat`, { method: 'POST', body: { text } })
