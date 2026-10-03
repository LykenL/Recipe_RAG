import type { Message, Source, TraceStep } from './types'

/**
 * Conversation sessions kept in localStorage.
 *
 * Why not the server: Render's free Postgres expires after 30 days (data is
 * deleted 14 days later) and free instances have no persistent disk, so
 * server-side storage would either cost money or silently lose history. For a
 * project meant to stay online and be shown to people, the browser is the only
 * option that is both free and durable. The trade-off is that history is
 * per-browser, not per-account.
 *
 * Everything here is best-effort: Safari private mode and a full quota both
 * throw on write, and losing history must never break the chat itself.
 */

export interface Session {
  id: string
  title: string
  createdAt: number
  updatedAt: number
  messages: Message[]
}

const SESSIONS_KEY = 'mise.sessions.v1'
const ACTIVE_KEY = 'mise.activeSession.v1'
/** Keep the newest N; localStorage is ~5MB and a session is not tiny. */
const MAX_SESSIONS = 30

const uid = () =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

/**
 * Drop the fields that are large and re-derivable.
 *
 * `full_text` is up to 6KB per source, so a single answer could be ~25KB and
 * thirty of them would blow the quota. The snippet is kept so expanded cards
 * still show something after a reload.
 */
function slimMessage(m: Message): Message {
  return {
    ...m,
    pending: false,
    sources: (m.sources ?? []).map(({ full_text: _drop, ...rest }) => rest as Source),
    trace: (m.trace ?? []).map(({ sources: _alsoDrop, ...rest }) => rest as TraceStep),
  }
}

function read<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function write(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* quota exceeded or storage disabled — history is a nice-to-have */
  }
}

export function loadSessions(): Session[] {
  const list = read<Session[]>(SESSIONS_KEY, [])
  if (!Array.isArray(list)) return []
  return list
    .filter((s) => s && typeof s.id === 'string' && Array.isArray(s.messages))
    .sort((a, b) => b.updatedAt - a.updatedAt)
}

export function saveSessions(list: Session[]): void {
  const trimmed = [...list]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_SESSIONS)
    .map((s) => ({ ...s, messages: s.messages.map(slimMessage) }))
  write(SESSIONS_KEY, trimmed)
}

export function loadActiveId(): string | null {
  return read<string | null>(ACTIVE_KEY, null)
}

export function saveActiveId(id: string | null): void {
  write(ACTIVE_KEY, id)
}

export function newSession(): Session {
  const now = Date.now()
  return { id: uid(), title: 'New conversation', createdAt: now, updatedAt: now, messages: [] }
}

/** Title = the first thing the user asked, trimmed to fit the rail. */
export function deriveTitle(messages: Message[]): string {
  const first = messages.find((m) => m.role === 'user' && m.content.trim())
  if (!first) return 'New conversation'
  const text = first.content.replace(/\s+/g, ' ').trim()
  return text.length > 42 ? `${text.slice(0, 42)}…` : text
}
