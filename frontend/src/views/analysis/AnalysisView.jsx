import { useState } from 'react'
import { ANALYSIS_STATUS } from '../../constants/analysisStatus.js'
import { formatDate } from '../../utils/format.js'
import PageHeader from '../../components/layout/PageHeader.jsx'
import Panel from '../../components/ui/Panel.jsx'
import Tabs from '../../components/ui/Tabs.jsx'
import Tag from '../../components/ui/Tag.jsx'
import AnalysisProgress from './AnalysisProgress.jsx'
import ChatTab from './ChatTab.jsx'
import ReportTab from './ReportTab.jsx'
import TracesTab from './TracesTab.jsx'

const TABS = {
  Informe: ReportTab,
  'Trazas de ejecución': TracesTab,
  Chat: ChatTab,
}

/** Análisis abierto: progreso mientras se ejecuta; informe, trazas y chat al terminar. */
export default function AnalysisView({ analysis, onUpdate, onCancel }) {
  const [tab, setTab] = useState('Informe')

  if (analysis.status !== 'complete') {
    return <AnalysisProgress analysis={analysis} onCancel={onCancel} />
  }

  const status = ANALYSIS_STATUS[analysis.status]
  const TabContent = TABS[tab]

  return (
    <section>
      <PageHeader
        eyebrow={`${analysis.name} · ${formatDate(analysis.createdAt)}`}
        title="Informe del cambio"
        aside={<Tag status={status.tag}>{status.label}</Tag>}
      />

      <Panel className="pt-2! md:pt-2!">
        <Tabs tabs={Object.keys(TABS)} selected={tab} onSelect={setTab} label="Vistas del análisis" />
        <div role="tabpanel" aria-label={tab} className="pt-6">
          <TabContent analysis={analysis} onUpdate={onUpdate} />
        </div>
      </Panel>
    </section>
  )
}
