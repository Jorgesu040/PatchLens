/** Casilla dentro de una caja que se colorea cuando está marcada. */
export default function Checkbox({ label, checked, onChange }) {
  return (
    <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xs border border-border bg-ink px-2.5 text-xs has-checked:border-accent has-checked:bg-selection">
      <input
        type="checkbox"
        className="size-4 accent-accent"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label}
    </label>
  )
}
