/** Cabecera de página: antetítulo, título, introducción y un elemento a la derecha. */
export default function PageHeader({ eyebrow, title, intro, aside }) {
  return (
    <header className="relative mb-6 flex flex-wrap items-start justify-between gap-4 border-b border-border pb-6 after:absolute after:-bottom-0.5 after:left-0 after:h-[3px] after:w-30 after:bg-accent">
      <div className="max-w-3xl">
        {eyebrow && (
          <p className="mb-2 font-mono text-[11px] font-semibold tracking-[.12em] break-all text-accent uppercase">
            {eyebrow}
          </p>
        )}
        <h1 className="font-display text-[clamp(31px,3vw,46px)] leading-tight font-extrabold tracking-[.035em] uppercase">
          {title}
        </h1>
        {intro && <p className="mt-3 text-muted">{intro}</p>}
      </div>
      {aside}
    </header>
  )
}
