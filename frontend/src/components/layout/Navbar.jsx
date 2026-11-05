import logo from '../../assets/logo-horizontal.svg'

function NavItem({ active = false, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={`flex min-h-11 w-full min-w-0 flex-col justify-center overflow-hidden rounded-xs px-3 text-left text-sm ${
        active ? 'border-l-3 border-accent bg-selection text-fg' : 'text-muted hover:bg-raised hover:text-fg'
      }`}
    >
      {children}
    </button>
  )
}

/** Barra lateral: nuevo análisis, guardados (con sublista), análisis abierto y credenciales. */
export default function Navbar({ view, analyses, openAnalysis, onNavigate, onOpen }) {
  return (
    <nav
      aria-label="Navegación principal"
      className="min-w-0 overflow-x-hidden border-b border-border bg-ink p-4 md:sticky md:top-0 md:h-screen md:overflow-y-auto md:border-r md:border-b-0 md:py-7"
    >
      <img src={logo} alt="PatchLens" width="195" height="32" className="mb-4 w-40 md:mb-10 md:w-48" />
      <p className="mb-2 hidden px-3 text-[11px] tracking-[.1em] text-muted uppercase md:block">
        Espacio de trabajo
      </p>

      <ul className="flex min-w-0 flex-wrap gap-1 md:flex-col">
        <li className="min-w-0">
          <NavItem active={view === 'new'} onClick={() => onNavigate('new')}>
            <span className="truncate">Nuevo análisis</span>
          </NavItem>
        </li>

        <li className="min-w-0">
          <NavItem active={view === 'saved'} onClick={() => onNavigate('saved')}>
            <span className="truncate">Análisis guardados</span>
          </NavItem>
          {analyses.length > 0 && (
            <ul className="mt-1 ml-3 hidden min-w-0 border-l border-border pl-2 md:block">
              {analyses.map((analysis) => (
                <li key={analysis.id} className="min-w-0">
                  <button
                    type="button"
                    title={analysis.name}
                    onClick={() => onOpen(analysis.id)}
                    className="block min-h-9 w-full truncate rounded-xs px-2 text-left font-mono text-xs text-muted hover:bg-raised hover:text-fg"
                  >
                    {analysis.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </li>

        {openAnalysis && (
          <li className="min-w-0">
            <NavItem active={view === 'analysis'} onClick={() => onNavigate('analysis')}>
              <span className="truncate">Análisis abierto</span>
              <span
                title={openAnalysis.name}
                className="block w-full truncate font-mono text-[11px] text-muted"
              >
                {openAnalysis.name}
              </span>
            </NavItem>
          </li>
        )}

        <li className="min-w-0 md:mt-4 md:border-t md:border-border md:pt-3">
          <NavItem active={view === 'credentials'} onClick={() => onNavigate('credentials')}>
            <span className="truncate">Credenciales y API</span>
          </NavItem>
        </li>
      </ul>
    </nav>
  )
}
