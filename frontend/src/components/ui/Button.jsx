const STATES = {
  primary:
    'border-action bg-action text-ink hover:border-action-hover hover:bg-action-hover hover:-translate-y-px active:translate-y-px motion-reduce:transform-none',
  default: 'border-border bg-raised text-fg hover:border-accent hover:bg-selection',
  disabled: 'border-border bg-raised text-fg opacity-50 cursor-not-allowed',
  loading: 'border-border bg-raised text-fg opacity-50 cursor-wait',
}

/**
 * Botón con 4 estados: primary | default | disabled | loading.
 * `disabled` y `loading` desactivan el botón.
 */
export default function Button({ state = 'default', type = 'button', className = '', children, ...props }) {
  const inactive = state === 'disabled' || state === 'loading'

  return (
    <button
      type={type}
      disabled={inactive}
      aria-busy={state === 'loading' || undefined}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xs border px-3.5 text-xs font-semibold ${STATES[state]} ${className}`}
      {...props}
    >
      {state === 'loading' && (
        <span
          aria-hidden="true"
          className="size-3 animate-spin rounded-full border-2 border-current border-r-transparent motion-reduce:animate-none"
        />
      )}
      {children}
    </button>
  )
}
