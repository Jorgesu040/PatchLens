import { useEffect, useState } from 'react'
import { ANALYSIS_STATUS } from '../../constants/analysisStatus.js'
import { RUN_STEPS, STAGES } from '../../constants/stages.js'
import { formatElapsed, formatOffset } from '../../utils/format.js'
import PageHeader from '../../components/layout/PageHeader.jsx'
import Button from '../../components/ui/Button.jsx'
import Panel from '../../components/ui/Panel.jsx'
import StateMessage from '../../components/ui/StateMessage.jsx'
import Tag from '../../components/ui/Tag.jsx'

const DOTS = {
  done: 'border-add bg-add',
  current: 'border-[5px] border-action bg-ink',
  pending: 'border-muted bg-transparent',
}

/** Instante actual, refrescado cada segundo mientras `active`. */
function useNow(active) {
  const [now, setNow] = useState(Date.now)
  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [active])
  return now
}

function StageList({ currentStage, running }) {
  const stateOf = (index) =>
    index < currentStage ? 'done' : index === currentStage && running ? 'current' : 'pending'

  return (
    <ol className="grid">
      {STAGES.map((name, index) => {
        const state = stateOf(index)
        return (
          <li
            key={name}
            className="relative flex items-center gap-3 pb-6 last:pb-0 not-last:after:absolute not-last:after:top-5 not-last:after:left-[9.5px] not-last:after:h-[calc(100%-20px)] not-last:after:w-px not-last:after:bg-border"
          >
            <span aria-hidden="true" className={`size-5 shrink-0 rounded-full border-2 ${DOTS[state]}`} />
            <span className={state === 'pending' ? 'text-muted' : state === 'current' ? 'font-semibold' : ''}>
              {name}
              <span className="sr-only"> · {{ done: 'completada', current: 'en curso', pending: 'pendiente' }[state]}</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

/** Progreso de un análisis en curso o detenido: etapas y registro de actividad. */
export default function AnalysisProgress({ analysis, onCancel }) {
  const running = analysis.status === 'running'
  const now = useNow(running)
  const status = ANALYSIS_STATUS[analysis.status]
  const currentStage = RUN_STEPS[analysis.stepIndex].stage

  return (
    <section>
      <PageHeader
        eyebrow={analysis.name}
        title={running ? 'Análisis en curso' : 'Análisis detenido'}
        intro={
          running
            ? 'Comparando las dos versiones. El informe estará disponible al terminar.'
            : 'Se conservan el registro y la configuración parcial. No se ha generado un informe.'
        }
        aside={<Tag status={status.tag}>{status.label}</Tag>}
      />

      <div className="grid gap-5 md:grid-cols-2">
        <Panel title="Etapas">
          <p className="-mt-3 mb-6 text-sm text-muted">
            Tiempo transcurrido:{' '}
            <span className="font-mono text-fg">
              {formatElapsed(analysis.startedAt, analysis.endedAt ?? now)}
            </span>
          </p>
          <StageList currentStage={currentStage} running={running} />
        </Panel>

        <Panel title="Registro de actividad" description="Mensajes públicos del proceso">
          <ol aria-live="polite" className="mb-6">
            {analysis.logs.map((log, index) => (
              <li key={index} className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-4 border-t border-border py-4 text-sm">
                <time className="font-mono text-muted">{formatOffset(analysis.startedAt, log.at)}</time>
                <span>{log.text}</span>
              </li>
            ))}
          </ol>

          {running ? (
            <Button onClick={onCancel}>Cancelar análisis</Button>
          ) : (
            <StateMessage kind="error" title="Resultado parcial">
              Análisis detenido por el usuario. Los hallazgos no se presentan como verificados.
            </StateMessage>
          )}
        </Panel>
      </div>
    </section>
  )
}
