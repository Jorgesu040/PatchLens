import { useState } from 'react'
import { sendMessage } from '../../api/analyses.js'
import Chat from '../../components/chat/Chat.jsx'

/**
 * Conversación sobre el análisis. Los mensajes se guardan en el propio análisis
 * para no perderlos al cambiar de pestaña. Respuesta esperada: { messages: [...] }.
 */
export default function ChatTab({ analysis, onUpdate }) {
  const [busy, setBusy] = useState(false)

  const addMessage = (message) =>
    onUpdate((record) => ({
      ...record,
      messages: [...record.messages, { id: crypto.randomUUID(), ...message }],
    }))

  async function handleSend(text) {
    addMessage({ role: 'user', kind: 'text', text })
    setBusy(true)
    try {
      const reply = await sendMessage(analysis.id, text)
      reply.messages.forEach(addMessage)
    } catch (error) {
      addMessage({ role: 'agent', kind: 'text', text: `No se pudo obtener respuesta: ${error.message}` })
    } finally {
      setBusy(false)
    }
  }

  return <Chat messages={analysis.messages} onSend={handleSend} busy={busy} />
}
