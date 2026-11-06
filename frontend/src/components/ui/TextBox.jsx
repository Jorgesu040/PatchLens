const ROLES = {
  agent: { label: 'Agente', className: 'border-l-2 border-accent bg-ink' },
  user: { label: 'Tú', className: 'bg-selection' },
}

/** Bloque de texto de una conversación: `agent` o `user`. */
export default function TextBox({ role, children }) {
  const { label, className } = ROLES[role]

  return (
    <div className={`rounded-xs px-3.5 py-2.5 text-sm ${className}`}>
      <span className="mb-1 block font-mono text-[10px] tracking-[.08em] text-muted uppercase">{label}</span>
      <p className="break-words whitespace-pre-wrap">{children}</p>
    </div>
  )
}
