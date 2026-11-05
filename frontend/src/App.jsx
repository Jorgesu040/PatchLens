import { useCallback, useState } from 'react'
import { RUN_STEPS } from './constants/stages.js'
import useSimulatedRun from './hooks/useSimulatedRun.js'
import Navbar from './components/layout/Navbar.jsx'
import CredentialsView from './views/CredentialsView.jsx'
import NewAnalysisView from './views/NewAnalysisView.jsx'
import SavedAnalysesView from './views/SavedAnalysesView.jsx'
import AnalysisView from './views/analysis/AnalysisView.jsx'

function createRecord({
  oldFile,
  newFile,
  projectName,
  engines,
  provider,
  model,
  maxIterations,
  timeout,
  requestError,
}) {
  const now = Date.now()
  const logs = [{ at: now, text: RUN_STEPS[0].text }]
  if (requestError) logs.push({ at: now, text: `Backend no disponible: ${requestError}` })

  return {
    id: crypto.randomUUID(),
    name: `${oldFile.name} → ${newFile.name}`,
    config: {
      oldFile: { name: oldFile.name, size: oldFile.size },
      newFile: { name: newFile.name, size: newFile.size },
      projectName,
      engines,
      provider,
      model,
      maxIterations,
      timeout,
    },
    status: 'running',
    createdAt: now,
    startedAt: now,
    endedAt: null,
    stepIndex: 0,
    logs,
    messages: [],
  }
}

export default function App() {
  const [view, setView] = useState('new')
  const [analyses, setAnalyses] = useState([])
  const [openId, setOpenId] = useState(null)

  const openAnalysis = analyses.find((analysis) => analysis.id === openId)
  const runningId = analyses.find((analysis) => analysis.status === 'running')?.id

  const updateAnalysis = useCallback((id, updater) => {
    setAnalyses((list) => list.map((analysis) => (analysis.id === id ? updater(analysis) : analysis)))
  }, [])

  useSimulatedRun(runningId, updateAnalysis)

  function openById(id) {
    setOpenId(id)
    setView('analysis')
  }

  function startAnalysis(config) {
    const record = createRecord(config)
    setAnalyses((list) => [record, ...list])
    openById(record.id)
  }

  function cancelAnalysis(id) {
    updateAnalysis(id, (analysis) => ({
      ...analysis,
      status: 'stopped',
      endedAt: Date.now(),
      logs: [...analysis.logs, { at: Date.now(), text: 'Análisis cancelado por el usuario.' }],
    }))
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
      <Navbar
        view={view}
        analyses={analyses}
        openAnalysis={openAnalysis}
        onNavigate={setView}
        onOpen={openById}
      />

      <main className="mx-auto w-full max-w-6xl min-w-0 px-5 py-8 md:px-10 md:py-10">
        {view === 'new' && <NewAnalysisView onStart={startAnalysis} />}
        {view === 'saved' && (
          <SavedAnalysesView analyses={analyses} onOpen={openById} onNew={() => setView('new')} />
        )}
        {view === 'credentials' && <CredentialsView />}
        {view === 'analysis' && openAnalysis && (
          <AnalysisView
            key={openAnalysis.id}
            analysis={openAnalysis}
            onUpdate={(updater) => updateAnalysis(openAnalysis.id, updater)}
            onCancel={() => cancelAnalysis(openAnalysis.id)}
          />
        )}
      </main>
    </div>
  )
}
