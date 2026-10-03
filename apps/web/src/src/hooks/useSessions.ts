import { useCallback, useEffect, useRef, useState } from 'react'
import {
  deriveTitle,
  loadActiveId,
  loadSessions,
  newSession,
  saveActiveId,
  saveSessions,
  type Session,
} from '../lib/sessions'
import type { Message } from '../lib/types'

export interface SessionStore {
  sessions: Session[]
  activeId: string | null
  active: Session | null
  create: () => void
  select: (id: string) => void
  remove: (id: string) => void
  rename: (id: string, title: string) => void
  /** persist the message list for a session; debounced by the caller */
  store: (id: string, messages: Message[]) => void
}

/**
 * Resolve the starting list and the starting active id *together*.
 *
 * Computing them in two independent useState initialisers is how you end up
 * with a session in the list, `activeId === null`, and therefore nothing ever
 * being persisted: the "create a session if storage is empty" branch and the
 * "pick the active id" branch disagree. One pass, one result.
 */
function bootstrap(): { list: Session[]; id: string } {
  const existing = loadSessions()
  const list = existing.length > 0 ? existing : [newSession()]
  const stored = loadActiveId()
  const id = stored && list.some((s) => s.id === stored) ? stored : list[0].id
  return { list, id }
}

export function useSessions(): SessionStore {
  const initial = useRef<{ list: Session[]; id: string } | null>(null)
  if (initial.current === null) initial.current = bootstrap()

  const [sessions, setSessions] = useState<Session[]>(initial.current.list)
  const [activeId, setActiveId] = useState<string | null>(initial.current.id)

  // Persist the list, but not on every keystroke of a streaming answer.
  const flush = useRef<number | undefined>(undefined)
  useEffect(() => {
    window.clearTimeout(flush.current)
    flush.current = window.setTimeout(() => saveSessions(sessions), 400)
    return () => window.clearTimeout(flush.current)
  }, [sessions])

  useEffect(() => {
    saveActiveId(activeId)
  }, [activeId])

  // Keep the active id pointing at something that exists (delete, or a
  // restored list from another tab).
  useEffect(() => {
    if (sessions.length === 0) {
      const fresh = newSession()
      setSessions([fresh])
      setActiveId(fresh.id)
      return
    }
    if (!activeId || !sessions.some((s) => s.id === activeId)) {
      setActiveId(sessions[0].id)
    }
  }, [sessions, activeId])

  const create = useCallback(() => {
    const session = newSession()
    setSessions((prev) => [session, ...prev])
    setActiveId(session.id)
  }, [])

  const select = useCallback((id: string) => setActiveId(id), [])

  const remove = useCallback((id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id))
  }, [])

  const rename = useCallback((id: string, title: string) => {
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)))
  }, [])

  const store = useCallback((id: string, messages: Message[]) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === id
          ? {
              ...s,
              messages,
              // a hand-renamed title should survive further messages
              title: s.title === 'New conversation' ? deriveTitle(messages) : s.title,
              updatedAt: Date.now(),
            }
          : s,
      ),
    )
  }, [])

  const active = sessions.find((s) => s.id === activeId) ?? null

  return { sessions, activeId, active, create, select, remove, rename, store }
}
