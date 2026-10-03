export type Role = 'user' | 'assistant'

/** One retrieved cookbook passage, with the score the UI displays. */
export interface Source {
  title: string
  score: number
  /** short excerpt, shown collapsed */
  snippet: string
  /** the entire passage, shown when the card is expanded */
  full_text?: string
  source: string
  category?: string
  area?: string
}

/** A single agent step: intent parsing, a tool call, or completion. */
export interface TraceStep {
  step: string
  label?: string
  query?: string
  hits?: number
  sources?: Source[]
  ms?: number
}

export interface Turn {
  role: Role
  content: string
}

export interface ChatRequest {
  message: string
  history: Turn[]
  persona: string
  dietary: string[]
  pantry: string[]
}

export interface DonePayload {
  answer: string
  citations: number
  searches: number
  index: number
  model: string
  elapsed_ms: number
}

export interface Message {
  id: string
  role: Role
  content: string
  trace: TraceStep[]
  sources: Source[]
  done?: DonePayload
  error?: string
  /** true while tokens are still arriving */
  pending?: boolean
}

export interface IndexInfo {
  count: number
  dim: number
  model: string
  backend: string
  k: number
  min_similarity: number
}

export interface KitchenSettings {
  persona: string
  dietary: string[]
  pantry: string[]
}
