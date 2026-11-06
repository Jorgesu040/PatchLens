import { useRef } from 'react'
import Button from './Button.jsx'
import { formatSize } from '../../utils/format.js'

/** Caja para elegir un archivo. `label` es la marca de orden (p. ej. "01 / ANTES"). */
export default function UploadBox({ label, title, subtitle, file, onFileChange }) {
  const inputRef = useRef(null)

  return (
    <div className="relative flex min-h-44 min-w-0 flex-col justify-between gap-4 overflow-hidden rounded-xs border border-border bg-ink p-4 pt-6">
      <span className="absolute top-4 right-4 font-mono text-[10px] font-semibold tracking-[.08em] text-accent">
        {label}
      </span>

      <div className="min-w-0">
        <p className="font-semibold">{title}</p>
        <p className="text-sm text-muted">{subtitle}</p>
        <p
          title={file ? `${file.name} · ${formatSize(file.size)}` : undefined}
          className="mt-3 truncate font-mono text-xs text-muted"
        >
          {file ? `${file.name} · ${formatSize(file.size)}` : 'Ningún archivo seleccionado'}
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        tabIndex={-1}
        className="sr-only"
        aria-label={`Seleccionar ${title.toLowerCase()}`}
        onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
      />
      <Button className="self-start" onClick={() => inputRef.current.click()}>
        {file ? 'Sustituir archivo' : 'Seleccionar archivo'}
      </Button>
    </div>
  )
}
