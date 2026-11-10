import { useEffect } from 'react'
import { RUN_STEPS, STEP_INTERVAL_MS } from '../constants/stages.js'

/** Avanza un paso: añade su mensaje al registro o, si no quedan pasos, completa el análisis. */
export function advanceRun(analysis) {
  const nextIndex = analysis.stepIndex + 1
  const step = RUN_STEPS[nextIndex]
  const now = Date.now()

  if (!step) return { ...analysis, status: 'complete', endedAt: now }
  return {
    ...analysis,
    stepIndex: nextIndex,
    logs: [...analysis.logs, { at: now, text: step.text }],
  }
}

/**
 * Simula el progreso del análisis `id` (sin backend) llamando a
 * `update(id, advanceRun)` a intervalos fijos. Se detiene cuando `id` es nulo.
 */
export default function useSimulatedRun(id, update) {
  useEffect(() => {
    if (!id) return
    const timer = setInterval(() => update(id, advanceRun), STEP_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [id, update])
}
