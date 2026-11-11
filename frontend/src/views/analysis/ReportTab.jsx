import { getReport } from '../../api/analyses.js'
import useFetch from '../../hooks/useFetch.js'
import StateMessage from '../../components/ui/StateMessage.jsx'

/** Informe del análisis. Su formato de presentación todavía no está definido. */
export default function ReportTab({ analysis }) {
  const { data, error, loading } = useFetch((signal) => getReport(analysis.id, signal), [analysis.id])

  if (loading) return <StateMessage kind="loading" title="Cargando informe…" />
  if (error) {
    return (
      <StateMessage kind="error" title="No se pudo cargar el informe">
        {error.message}
      </StateMessage>
    )
  }
  return (
    <StateMessage kind="empty" title="Informe recibido">
      {data ? 'El formato de presentación del informe aún no está definido.' : 'El informe está vacío.'}
    </StateMessage>
  )
}
