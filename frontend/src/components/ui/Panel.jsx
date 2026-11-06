/** Superficie con borde, título y descripción opcionales. */
export default function Panel({ title, description, className = '', children }) {
  return (
    <section className={`rounded-sm border border-border bg-surface p-6 md:p-9 ${className}`}>
      {title && <h2 className="font-display text-2xl font-extrabold">{title}</h2>}
      {description && <p className="mt-2 text-sm text-muted">{description}</p>}
      <div className={title || description ? 'mt-6' : ''}>{children}</div>
    </section>
  )
}
