import { listAnalyses } from '../api/analyses.js'
import { ANALYSIS_STATUS } from '../constants/analysisStatus.js'
import useFetch from '../hooks/useFetch.js'
import { formatDate } from '../utils/format.js'
import PageHeader from '../components/layout/PageHeader.jsx'
import Button from '../components/ui/Button.jsx'
import Panel from '../components/ui/Panel.jsx'
import StateMessage from '../components/ui/StateMessage.jsx'
import Tag from '../components/ui/Tag.jsx'

function AnalysisRow({ analysis, onOpen }) {
  const status = ANALYSIS_STATUS[analysis.status]

  return (
    <li className="grid items-center gap-3 border-t border-border py-4 first:border-t-0 md:grid-cols-[minmax(0,1fr)_auto_auto]">
      <div className="min-w-0">
        <h3 className="font-semibold break-all">{analysis.name}</h3>
        <p className="text-xs text-muted">{formatDate(analysis.createdAt)}</p>
      </div>
      <Tag status={status.tag}>{status.label}</Tag>
      <Button onClick={() => onOpen(analysis.id)}>Abrir análisis</Button>
    </li>
  )
}

/**
 * Lista los análisis de esta sesión junto con los del backend
 * (se espera el mismo formato de registro que crea App).
 */
export default function SavedAnalysesView({ analyses, onOpen, onNew }) {
  const { data, error, loading } = useFetch(listAnalyses)
  const all = [...analyses, ...(data ?? [])]

  return (
    <section>
      <PageHeader
        eyebrow="Historial"
        title="Análisis guardados"
        intro="Abre un análisis para consultar su informe, sus trazas o continuar la conversación."
        aside={<Button onClick={onNew}>Nuevo análisis</Button>}
      />

      <Panel>
        {all.length > 0 && (
          <ul className="mb-5">
            {all.map((analysis) => (
              <AnalysisRow key={analysis.id} analysis={analysis} onOpen={onOpen} />
            ))}
          </ul>
        )}

        {loading && <StateMessage kind="loading" title="Cargando análisis del servidor…" />}
        {error && (
          <StateMessage kind="error" title="No se pudieron cargar los análisis del servidor">
            {error.message}
          </StateMessage>
        )}
        {!loading && !all.length && (
          <div className="mt-5">
            <StateMessage kind="empty" title="Todavía no hay análisis guardados">
              Inicia un nuevo análisis para comparar dos versiones.
            </StateMessage>
          </div>
        )}
      </Panel>
    </section>
  )
}
