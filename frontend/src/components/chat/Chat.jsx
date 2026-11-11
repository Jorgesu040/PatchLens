import { useState } from 'react'
import Button from '../ui/Button.jsx'
import TextBox from '../ui/TextBox.jsx'
import ToolCallBox from '../ui/ToolCallBox.jsx'

/**
 * Conversación con el agente.
 * `messages`: [{ id, role: 'user' | 'agent', kind: 'text' | 'tool', text?, tool? }]
 * El agente se muestra a la izquierda; el usuario, a la derecha.
 */
export default function Chat({ messages, onSend, busy = false }) {
  const [text, setText] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    const value = text.trim()
    if (!value) return
    onSend(value)
    setText('')
  }

  return (
    <div className="flex min-h-[28rem] flex-col gap-4">
      <ol aria-live="polite" className="flex flex-1 flex-col gap-3">
        {messages.map((message) => (
          <li
            key={message.id}
            className={`w-full max-w-[83%] ${message.role === 'user' ? 'self-end' : 'self-start'}`}
          >
            {message.kind === 'tool' ? (
              <ToolCallBox {...message.tool} />
            ) : (
              <TextBox role={message.role}>{message.text}</TextBox>
            )}
          </li>
        ))}
      </ol>

      {!messages.length && (
        <p className="text-sm text-muted">Pregunta por los cambios detectados o por lo que queda sin comprobar.</p>
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
        <label htmlFor="chat-input" className="sr-only">
          Pregunta sobre este análisis
        </label>
        <input
          id="chat-input"
          type="text"
          autoComplete="off"
          placeholder="Pregunta sobre los cambios…"
          value={text}
          disabled={busy}
          onChange={(event) => setText(event.target.value)}
          className="h-11 min-w-0 rounded-xs border border-border bg-ink px-3 text-sm placeholder:text-muted focus:border-action"
        />
        <Button type="submit" state={busy ? 'loading' : 'primary'}>
          Enviar
        </Button>
      </form>
    </div>
  )
}
