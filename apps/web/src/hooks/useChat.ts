import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from '../lib/api'
import type { KitchenSettings, Message, Source, TraceStep, Turn } from '../lib/types'

const uid = () => Math.random().toString(36).slice(2, 10)

export interface ChatState {
  messages: Message[]
  streaming: boolean
  /** sources from the most recent assistant turn, for the drawer */
  sources: Source[]
  send: (text: string, settings: KitchenSettings) => Promise<void>
  stop: () => void
  reset: () => void
}

export function useChat(): ChatState {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  // Mirror of `messages` so `send` can build history without being recreated
  // on every token (which would restart the stream consumer).
  const messagesRef = useRef<Message[]>(messages)
  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  const patch = useCallback((id: string, fn: (m: Message) => Message) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)))
  }, [])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStreaming(false)
    setMessages((prev) => prev.map((m) => (m.pending ? { ...m, pending: false } : m)))
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStreaming(false)
    setMessages([])
  }, [])

  const send = useCallback(
    async (text: string, settings: KitchenSettings) => {
      const trimmed = text.trim()
      if (!trimmed || streaming) return

      // Only completed, non-error assistant turns are replayed as history.
      const history = messagesRef.current.flatMap<Turn>((m): Turn[] => {
        if (m.role === 'user') return [{ role: 'user', content: m.content }]
        if (m.role === 'assistant' && m.content && !m.error && !m.pending) {
          return [{ role: 'assistant', content: m.content }]
        }
        return []
      })

      const assistantId = uid()
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: 'user', content: trimmed, trace: [], sources: [] },
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          trace: [],
          sources: [],
          pending: true,
        },
      ])

      const controller = new AbortController()
      abortRef.current = controller
      setStreaming(true)

      const onTrace = (step: TraceStep) =>
        patch(assistantId, (m) => ({ ...m, trace: [...m.trace, step] }))
      const onSources = (sources: Source[]) => patch(assistantId, (m) => ({ ...m, sources }))
      const onToken = (t: string) => patch(assistantId, (m) => ({ ...m, content: m.content + t }))
      const onDone = (done: Message['done']) =>
        patch(assistantId, (m) => ({ ...m, done, pending: false }))
      const onError = (error: string) =>
        patch(assistantId, (m) => ({ ...m, error, pending: false }))

      try {
        await streamChat(
          {
            message: trimmed,
            history,
            persona: settings.persona,
            dietary: settings.dietary,
            pantry: settings.pantry,
          },
          { onTrace, onSources, onToken, onDone, onError },
          controller.signal,
        )
      } catch (err) {
        const e = err as Error
        if (e.name !== 'AbortError') {
          patch(assistantId, (m) => ({ ...m, error: e.message || String(err), pending: false }))
        } else {
          patch(assistantId, (m) => ({ ...m, pending: false }))
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null
        setStreaming(false)
        patch(assistantId, (m) => (m.pending ? { ...m, pending: false } : m))
      }
    },
    [patch, streaming],
  )

  // Abort an in-flight request if the tab is closed mid-stream.
  useEffect(() => () => abortRef.current?.abort(), [])

  const lastSources = [...messages].reverse().find((m) => m.role === 'assistant')?.sources ?? []

  return { messages, streaming, sources: lastSources, send, stop, reset }
}
