const SIDES = {
  before: { heading: '01 / ANTES', sign: '−', className: 'bg-delete-bg', signClass: 'text-delete' },
  after: { heading: '02 / DESPUÉS', sign: '+', className: 'bg-add-bg', signClass: 'text-add' },
}

function DiffColumn({ side, functionName, lines }) {
  const { heading, sign, className, signClass } = SIDES[side]

  return (
    <div className="min-w-0 not-first:border-t not-first:border-border md:not-first:border-t-0 md:not-first:border-l">
      <div className="border-b border-border px-3 py-2 font-mono text-[11px] font-semibold">
        {heading} · {functionName}
      </div>
      {lines.length ? (
        lines.map((line, index) => (
          <div key={index} className={`grid grid-cols-[20px_minmax(0,1fr)] px-2.5 py-1.5 font-mono text-xs ${className}`}>
            <span aria-hidden="true" className={signClass}>
              {sign}
            </span>
            <code className="break-words whitespace-pre-wrap">{line}</code>
          </div>
        ))
      ) : (
        <p className="px-3 py-2 text-xs text-muted">Sin código en esta versión.</p>
      )}
    </div>
  )
}

/** Comparación de código antes/después de una función. */
export default function DiffSection({ functionName, before = [], after = [] }) {
  return (
    <div
      role="group"
      aria-label={`Cambios en ${functionName}`}
      className="grid rounded-xs border border-border bg-ink md:grid-cols-2"
    >
      <DiffColumn side="before" functionName={functionName} lines={before} />
      <DiffColumn side="after" functionName={functionName} lines={after} />
    </div>
  )
}
