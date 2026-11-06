/** Estado del proceso → estado visual de <Tag>. */
export const ANALYSIS_STATUS = {
  running: { tag: 'running', label: 'En curso' },
  complete: { tag: 'add', label: 'Completado' },
  stopped: { tag: 'error', label: 'Detenido' },
}
