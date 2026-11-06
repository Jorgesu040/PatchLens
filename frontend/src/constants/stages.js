export const ENGINES = ['Version Tracking', 'Simple Diff', 'Structural Graph']

export const STAGES = ['Preparación', 'Comparación', 'Correlación', 'Consultas del agente', 'Informe']

/** Pasos del progreso simulado. `stage` es el índice en STAGES. */
export const RUN_STEPS = [
  { stage: 0, text: 'Preparación del contexto de análisis.' },
  { stage: 1, text: 'Version Tracking: propuestas de correspondencia y cambio.' },
  { stage: 1, text: 'Simple Diff: propuestas de cambio.' },
  { stage: 1, text: 'Structural Graph: propuestas estructurales.' },
  { stage: 2, text: 'Normalización y correlación de propuestas.' },
  { stage: 3, text: 'Consultas del agente sobre las funciones modificadas.' },
  { stage: 4, text: 'Redacción del informe.' },
]

export const STEP_INTERVAL_MS = 1500
