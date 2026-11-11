const KINDS = {
  loading: { role: 'status', className: 'border-border', titleClass: 'text-fg' },
  empty: { role: 'status', className: 'border-border', titleClass: 'text-fg' },
  error: { role: 'alert', className: 'border-delete', titleClass: 'text-delete' },
}

/** Estado explícito de una sección: loading | empty | error. */
export default function StateMessage({ kind, title, children }) {
  const { role, className, titleClass } = KINDS[kind]

  return (
    <div role={role} className={`rounded-xs border p-4 ${className}`}>
      <p className={`text-sm font-semibold ${titleClass}`}>{title}</p>
      {children && <p className="mt-1 text-xs text-muted">{children}</p>}
    </div>
  )
}
