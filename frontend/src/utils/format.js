const sizeFormat = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 })
const dateFormat = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })

export const formatSize = (bytes) => `${sizeFormat.format(bytes / 1024)} KB`

export const formatDate = (timestamp) => dateFormat.format(new Date(timestamp))

/** Segundos transcurridos entre `from` y `to`, formateados como "N s". */
export const formatElapsed = (from, to) => `${Math.max(0, Math.floor((to - from) / 1000))} s`

/** Como formatElapsed, con signo: "+N s". */
export const formatOffset = (from, to) => `+${formatElapsed(from, to)}`
