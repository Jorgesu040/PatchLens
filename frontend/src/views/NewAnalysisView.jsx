import { useState } from 'react'
import { createAnalysis } from '../api/analyses.js'
import { ENGINES } from '../constants/stages.js'
import PageHeader from '../components/layout/PageHeader.jsx'
import Button from '../components/ui/Button.jsx'
import Checkbox from '../components/ui/Checkbox.jsx'
import ModelPicker from '../components/ui/ModelPicker.jsx'
import Panel from '../components/ui/Panel.jsx'
import UploadBox from '../components/ui/UploadBox.jsx'

export default function NewAnalysisView({ onStart }) {
  const [files, setFiles] = useState({ old: null, new: null })
  const [projectName, setProjectName] = useState('')
  const [engines, setEngines] = useState(ENGINES)
  const [provider, setProvider] = useState('api-key')
  const [model, setModel] = useState('')
  const [maxIterations, setMaxIterations] = useState(6)
  const [timeout, setTimeoutSeconds] = useState(1800)
  const [submitting, setSubmitting] = useState(false)

  const validLimits = Number(maxIterations) > 0 && Number(timeout) > 0
  const canStart = files.old && files.new && engines.length > 0 && validLimits
  const buttonState = submitting ? 'loading' : canStart ? 'primary' : 'disabled'

  const setFile = (side) => (file) => setFiles((current) => ({ ...current, [side]: file }))

  function toggleEngine(engine, checked) {
    setEngines((current) => ENGINES.filter((item) => (item === engine ? checked : current.includes(item))))
  }

  async function handleStart() {
    const config = {
      oldFile: files.old,
      newFile: files.new,
      projectName: projectName.trim() || `${files.old.name}-vs-${files.new.name}`,
      engines,
      provider,
      model,
      maxIterations: Number(maxIterations),
      timeout: Number(timeout),
    }
    setSubmitting(true)

    let requestError = null
    try {
      await createAnalysis(config)
    } catch (error) {
      requestError = error.message
    }

    setSubmitting(false)
    onStart({ ...config, requestError })
  }

  return (
    <section>
      <PageHeader
        eyebrow="Comparación semántica"
        title="Nuevo análisis"
        intro="Compara dos versiones compiladas y organiza propuestas de cambio, consecuencias funcionales y evidencias en un mismo contexto."
      />

      <div className="grid gap-5">
        <Panel title="Versiones a comparar" description="Orden de referencia para el informe">
          <div className="grid gap-4 md:grid-cols-2">
            <UploadBox
              label="01 / ANTES"
              title="Versión anterior"
              subtitle="Binario ELF x86-64"
              file={files.old}
              onFileChange={setFile('old')}
            />
            <UploadBox
              label="02 / DESPUÉS"
              title="Versión nueva"
              subtitle="Binario ELF x86-64"
              file={files.new}
              onFileChange={setFile('new')}
            />
          </div>
        </Panel>

        <Panel
          title="Opciones de análisis y agente"
          description="Motores de Ghidriff, proveedor/modelo de inferencia y límites de ejecución (Main.py)"
        >
          <div className="grid gap-5">
            <div>
              <p className="mb-2 text-xs font-semibold text-fg">Motores de diferencias</p>
              <div className="flex flex-wrap gap-2">
                {ENGINES.map((engine) => (
                  <Checkbox
                    key={engine}
                    label={engine}
                    checked={engines.includes(engine)}
                    onChange={(checked) => toggleEngine(engine, checked)}
                  />
                ))}
              </div>
            </div>

            <ModelPicker
              provider={provider}
              model={model}
              onProviderChange={setProvider}
              onModelChange={setModel}
            />

            <div className="grid gap-4 md:grid-cols-3">
              <label className="flex flex-col gap-1.5 text-xs">
                <span className="font-semibold text-fg">Nombre del proyecto</span>
                <input
                  type="text"
                  value={projectName}
                  placeholder="Opcional (ej. mi_comparacion)"
                  onChange={(event) => setProjectName(event.target.value)}
                  className="h-11 rounded-xs border border-border bg-ink px-3 font-mono text-sm text-fg placeholder:text-muted focus:border-action"
                />
              </label>

              <label className="flex flex-col gap-1.5 text-xs">
                <span className="font-semibold text-fg">Iteraciones máximas</span>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={maxIterations}
                  onChange={(event) => setMaxIterations(event.target.value)}
                  className="h-11 rounded-xs border border-border bg-ink px-3 font-mono text-sm text-fg focus:border-action"
                />
              </label>

              <label className="flex flex-col gap-1.5 text-xs">
                <span className="font-semibold text-fg">Tiempo límite por motor (s)</span>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={timeout}
                  onChange={(event) => setTimeoutSeconds(event.target.value)}
                  className="h-11 rounded-xs border border-border bg-ink px-3 font-mono text-sm text-fg focus:border-action"
                />
              </label>
            </div>
          </div>
        </Panel>

        <div className="flex justify-end">
          <Button state={buttonState} onClick={handleStart}>
            Iniciar análisis
          </Button>
        </div>
      </div>
    </section>
  )
}
