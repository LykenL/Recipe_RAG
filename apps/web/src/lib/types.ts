export type Role = 'user' | 'assistant'

/** One retrieved cookbook passage, with the score the UI displays. */
export interface Source {
  title: string
  score: number
  /** short excerpt, shown collapsed */
  snippet: string
  /** the entire passage, shown when the card is expanded */
  full_text?: string
  /** TheMealDB thumbnail for this dish, when the corpus has one */
  image?: string
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

/** A dish shown in the empty state's browse strip. */
export interface SampleDish {
  title: string
  image: string
  category: string
  area: string
}

/** One card in the browse grid. */
export interface RecipeSummary {
  id: number
  title: string
  image: string
  category: string
  area: string
  /** cosine score; null when browsing rather than searching */
  score?: number | null
}

export interface Facet {
  value: string
  count: number
}

export interface RecipeList {
  total: number
  page: number
  page_size: number
  has_more: boolean
  query: string
  items: RecipeSummary[]
  facets: { category: Facet[]; area: Facet[] }
}

export interface RecipeDetail extends RecipeSummary {
  ingredients: string
  instructions: string
  notes: string
  serving_size: number[] | null
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
