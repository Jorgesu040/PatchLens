/** Pestañas controladas. Recibe la lista de nombres, la seleccionada y `onSelect(nombre)`. */
export default function Tabs({ tabs, selected, onSelect, label }) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-5 border-b border-border">
      {tabs.map((tab) => {
        const active = tab === selected
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onSelect(tab)}
            className={`-mb-px min-h-11 border-b-2 text-xs font-semibold ${
              active ? 'border-accent text-fg' : 'border-transparent text-muted hover:text-fg'
            }`}
          >
            {tab}
          </button>
        )
      })}
    </div>
  )
}
