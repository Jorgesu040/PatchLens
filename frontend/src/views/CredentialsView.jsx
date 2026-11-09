import { useState } from 'react'
import { clearApiKey, getAuthStatus, loginChatGPT, logoutChatGPT, setApiKey } from '../api/auth.js'
import useFetch from '../hooks/useFetch.js'
import PageHeader from '../components/layout/PageHeader.jsx'
import Button from '../components/ui/Button.jsx'
import Panel from '../components/ui/Panel.jsx'
import StateMessage from '../components/ui/StateMessage.jsx'
import Tag from '../components/ui/Tag.jsx'

export default function CredentialsView() {
  const [refreshKey, setRefreshKey] = useState(0)
  const { data: status, error: statusError, loading } = useFetch(getAuthStatus, [refreshKey])

  const [apiKeyInput, setApiKeyInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState(null)

  async function runAction(fn, getMessage) {
    setBusy(true)
    setFeedback(null)
    try {
      const result = await fn()
      setFeedback(getMessage(result))
      setRefreshKey((k) => k + 1)
    } catch (error) {
      setFeedback({ kind: 'error', title: 'Error de comunicación con el backend', detail: error.message })
    } finally {
      setBusy(false)
    }
  }

  function handleSaveKey(event) {
    event.preventDefault()
    const trimmed = apiKeyInput.trim()
    if (!trimmed) return
    runAction(
      () => setApiKey(trimmed),
      (res) => ({
        kind: res?.valid ? 'empty' : 'error',
        title: res?.valid ? 'OPENAI_API_KEY guardada y verificada.' : 'La OPENAI_API_KEY no es válida.',
      }),
    )
    setApiKeyInput('')
  }

  const account = status?.account
  const apiKey = status?.apiKey

  return (
    <section>
      <PageHeader
        eyebrow="Autenticación de inferencia"
        title="Credenciales y API"
        intro="Configura la sesión OAuth de ChatGPT (.patchlens-auth) o la clave OPENAI_API_KEY que utiliza el agente de PatchLens."
      />

      <div className="grid gap-5">
        {feedback && (
          <StateMessage kind={feedback.kind} title={feedback.title}>
            {feedback.detail}
          </StateMessage>
        )}

        <Panel title="Estado en el servidor" description="Consulta a GET /api/auth/status">
          {loading && <StateMessage kind="loading" title="Comprobando credenciales…" />}
          {statusError && (
            <StateMessage kind="error" title="No se pudo consultar el estado de autenticación">
              {statusError.message}
            </StateMessage>
          )}
          {status && (
            <div className="flex flex-wrap gap-3">
              <Tag status={account?.logged && !account?.expired ? 'add' : account?.expired ? 'error' : 'running'}>
                ChatGPT OAuth:{' '}
                {account?.logged
                  ? account.expired
                    ? 'Sesión expirada'
                    : `Activa${account.email ? ` (${account.email})` : ''}`
                  : 'Sin sesión'}
              </Tag>
              <Tag status={apiKey?.valid ? 'add' : apiKey?.configured ? 'error' : 'running'}>
                OPENAI_API_KEY:{' '}
                {apiKey?.configured ? (apiKey.valid ? 'Válida' : 'Inválida') : 'No configurada'}
              </Tag>
            </div>
          )}
        </Panel>

        <Panel
          title="Sesión de ChatGPT (OAuth)"
          description="Equivalente a ejecutar python AI.py login / logout. Autoriza el uso de tu cuenta mediante OAuth PKCE."
        >
          <div className="flex flex-wrap gap-3">
            <Button
              state={busy ? 'loading' : 'primary'}
              onClick={() =>
                runAction(loginChatGPT, (res) => ({
                  kind: res?.logged ? 'empty' : 'error',
                  title: res?.logged ? 'Sesión de ChatGPT iniciada.' : 'No se pudo iniciar sesión.',
                }))
              }
            >
              Iniciar sesión con ChatGPT
            </Button>
            <Button
              state={busy ? 'loading' : 'default'}
              onClick={() =>
                runAction(logoutChatGPT, (res) => ({
                  kind: res?.completed ? 'empty' : 'error',
                  title: res?.completed ? 'Sesión de ChatGPT cerrada.' : 'No se pudo cerrar la sesión.',
                }))
              }
            >
              Cerrar sesión
            </Button>
          </div>
        </Panel>

        <Panel
          title="OpenAI API Key"
          description="Para usar --provider api-key. La clave se envía al backend y no se almacena en el navegador."
        >
          <form onSubmit={handleSaveKey} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto]">
            <label htmlFor="openai-api-key" className="sr-only">
              OpenAI API Key
            </label>
            <input
              id="openai-api-key"
              type="password"
              autoComplete="off"
              placeholder="sk-..."
              value={apiKeyInput}
              onChange={(event) => setApiKeyInput(event.target.value)}
              className="h-11 min-w-0 rounded-xs border border-border bg-ink px-3 font-mono text-sm text-fg placeholder:text-muted focus:border-action"
            />
            <Button
              type="submit"
              state={busy ? 'loading' : apiKeyInput.trim() ? 'primary' : 'disabled'}
            >
              Guardar clave
            </Button>
            <Button
              state={busy ? 'loading' : 'default'}
              onClick={() =>
                runAction(clearApiKey, (res) => ({
                  kind: res?.completed ? 'empty' : 'error',
                  title: res?.completed ? 'OPENAI_API_KEY eliminada del servidor.' : 'No se pudo eliminar la clave.',
                }))
              }
            >
              Eliminar clave
            </Button>
          </form>
        </Panel>
      </div>
    </section>
  )
}
