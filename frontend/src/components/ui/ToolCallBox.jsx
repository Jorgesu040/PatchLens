const STATUSES = {
  ok: { label: 'Completada', className: 'text-add' },
  running: { label: 'En curso', className: 'text-muted' },
  error: { label: 'Error', className: 'text-delete' },
}

const toText = (value) => (typeof value === 'string' ? value : JSON.stringify(value, null, 2))

function Detail({ title, value }) {
  return (
    <div>
      <p className="mb-1 font-semibold tracking-[.08em] text-muted uppercase">{title}</p>
      <pre className="overflow-x-auto rounded-xs bg-surface p-2.5 text-xs whitespace-pre-wrap text-fg">
        {value === undefined ? 'Sin datos' : toText(value)}
      </pre>
    </div>
  )
}

/** Consulta visible del agente. Se expande para ver la llamada y su resultado. */
export default function ToolCallBox({ name, target, status = 'ok', args, result }) {
  const { label, className } = STATUSES[status]

  return (
    <details className="group rounded-xs border border-border bg-ink font-mono text-[11px]">
      <summary className="grid cursor-pointer list-none grid-cols-[80px_minmax(0,1fr)_auto] items-center gap-2.5 p-3 hover:bg-raised [&::-webkit-details-marker]:hidden">
        <span className="text-accent">CONSULTA</span>
        <strong className="font-medium break-words">
          {name}
          {target && ` · ${target}`}
        </strong>
        <span className={className}>
          {label}{' '}
          <span aria-hidden="true" className="inline-block text-muted group-open:rotate-180">
            ▾
          </span>
        </span>
      </summary>
      <div className="grid gap-3 border-t border-border p-3">
        <Detail title="Llamada" value={args} />
        <Detail title="Resultado" value={result} />
      </div>
    </details>
  )
}
