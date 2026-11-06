import { listModels } from '../../api/models.js'
import useFetch from '../../hooks/useFetch.js'

const PROVIDERS = [
  { id: 'chatgpt', label: 'Sesión ChatGPT (OAuth)' },
  { id: 'api-key', label: 'OpenAI API Key' },
]

/** Selector de proveedor ('chatgpt' | 'api-key') y modelo (`GET /api/models?provider=...`). */
export default function ModelPicker({ provider, model, onProviderChange, onModelChange }) {
  const { data, error } = useFetch((signal) => listModels(provider, signal), [provider])
  const models = data ?? []

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <label className="flex flex-col gap-1.5 text-xs">
        <span className="font-semibold text-fg">Proveedor de inferencia</span>
        <select
          value={provider}
          onChange={(event) => onProviderChange(event.target.value)}
          className="h-11 rounded-xs border border-border bg-ink px-3 text-sm text-fg focus:border-action"
        >
          {PROVIDERS.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1.5 text-xs">
        <span className="font-semibold text-fg">Modelo del agente</span>
        <select
          value={model}
          onChange={(event) => onModelChange(event.target.value)}
          className="h-11 rounded-xs border border-border bg-ink px-3 font-mono text-sm text-fg focus:border-action"
        >
          <option value="">Sin agente IA (solo motores)</option>
          {models.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        {error && <span className="text-[11px] text-delete">{error.message}</span>}
      </label>
    </div>
  )
}
