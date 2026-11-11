import { getTraces } from '../../api/analyses.js'
import useFetch from '../../hooks/useFetch.js'
import { formatOffset, formatSize } from '../../utils/format.js'
import StateMessage from '../../components/ui/StateMessage.jsx'
import ToolCallBox from '../../components/ui/ToolCallBox.jsx'

function Section({ title, children }) {
  return (
    <section className="border-t border-border pt-5 first:border-t-0 first:pt-0">
      <h3 className="mb-3 font-semibold">{title}</h3>
      {children}
    </section>
  )
}

/**
 * Trazas de ejecución: configuración, registro local del proceso y
 * consultas del agente devueltas por el backend ([{ id, name, target, status, args, result }]).
 */
export default function TracesTab({ analysis }) {
  const { data, error, loading } = useFetch((signal) => getTraces(analysis.id, signal), [analysis.id])
  const { oldFile, newFile, projectName, engines, provider, model, maxIterations, timeout } = analysis.config

  return (
    <div className="grid gap-5">
      <Section title="Configuración">
        <ul className="grid gap-1 text-sm text-muted">
          {projectName && (
            <li>
              Proyecto: <span className="font-mono text-fg">{projectName}</span>
            </li>
          )}
          <li>
            Anterior: <span className="font-mono text-fg">{oldFile.name}</span> · {formatSize(oldFile.size)}
          </li>
          <li>
            Nueva: <span className="font-mono text-fg">{newFile.name}</span> · {formatSize(newFile.size)}
          </li>
          <li>Motores: {engines.join(', ')}</li>
          <li>
            Modelo:{' '}
            <span className="font-mono text-fg">
              {model ? `${model} (${provider})` : 'Sin agente IA (solo motores)'}
            </span>
          </li>
          <li>
            Límites: {maxIterations} iteraciones máx. · {timeout} s por motor
          </li>
        </ul>
      </Section>

      <Section title="Mensajes del programa">
        <ol className="grid gap-1 text-sm">
          {analysis.logs.map((log, index) => (
            <li key={index} className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-4">
              <time className="font-mono text-muted">{formatOffset(analysis.startedAt, log.at)}</time>
              <span>{log.text}</span>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="Consultas del agente">
        {loading && <StateMessage kind="loading" title="Cargando consultas…" />}
        {error && (
          <StateMessage kind="error" title="No se pudieron cargar las consultas del agente">
            {error.message}
          </StateMessage>
        )}
        {data?.toolCalls && (
          <div className="grid gap-2">
            {data.toolCalls.map((call) => (
              <ToolCallBox key={call.id} {...call} />
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}
