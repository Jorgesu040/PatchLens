const STATUSES = {
  add: { label: '+ Añadido', className: 'border-add text-add' },
  delete: { label: '− Eliminado', className: 'border-delete text-delete' },
  modify: { label: '~ Modificado', className: 'border-accent text-accent' },
  running: { label: 'En curso', className: 'border-border text-muted' },
  error: { label: 'Error', className: 'border-delete text-delete' },
}

/**
 * Etiqueta de estado o categoría: add | delete | modify | running | error.
 * El texto siempre acompaña al color; `children` sustituye el texto por defecto.
 */
export default function Tag({ status, children }) {
  const { label, className } = STATUSES[status]

  return (
    <span className={`inline-flex items-center rounded-xs border px-2 py-1 font-mono text-[11px] ${className}`}>
      {children ?? label}
    </span>
  )
}
