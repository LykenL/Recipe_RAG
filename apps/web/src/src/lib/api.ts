import type { ChatRequest, DonePayload, IndexInfo, SampleDish, Source, TraceStep } from './types'

// Same-origin in production (FastAPI serves dist/), Vite proxy in dev.
const BASE = import.meta.env.VITE_API_BASE ?? ''

export interface StreamHandlers {
  onTrace?: (step: TraceStep) => void
  onSources?: (sources: Source[]) => void
  onToken?: (text: string) => void
  onDone?: (payload: DonePayload) => void
  onError?: (message: string) => void
}

export async function fetchSamples(n = 6, signal?: AbortSignal): Promise<SampleDish[]> {
  const res = await fetch(`${BASE}/api/recipes/sample?n=${n}`, { signal })
  if (!res.ok) return []
  return (await res.json()) as SampleDish[]
}

export async function fetchIndexInfo(signal?: AbortSignal): Promise<IndexInfo> {
  const res = await fetch(`${BASE}/api/index`, { signal })
  if (!res.ok) throw new Error(`GET /api/index -> ${res.status}`)
  return (await res.json()) as IndexInfo
}

/**
 * POST /api/chat and consume the SSE stream.
 *
 * EventSource cannot be used here because it only issues GET requests, and the
 * chat payload (message + history + kitchen settings) belongs in a body.
 */
export async function streamChat(
  req: ChatRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(req),
    signal,
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`POST /api/chat -> ${res.status}${detail ? `: ${detail.slice(0, 200)}` : ''}`)
  }
  if (!res.body) throw new Error('Streaming is not supported by this browser.')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE frames are separated by a blank line.
      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        dispatch(buffer.slice(0, boundary), handlers)
        buffer = buffer.slice(boundary + 2)
        boundary = buffer.indexOf('\n\n')
      }
    }
    if (buffer.trim()) dispatch(buffer, handlers)
  } finally {
    reader.cancel().catch(() => {})
  }
}

function dispatch(frame: string, handlers: StreamHandlers): void {
  let event = 'message'
  const dataLines: string[] = []

  for (const line of frame.split('\n')) {
    if (line.startsWith(':')) continue // comment / keep-alive
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
  }
  if (dataLines.length === 0) return

  let data: unknown
  try {
    data = JSON.parse(dataLines.join('\n'))
  } catch {
    return // a partial frame; the next read will complete it
  }

  switch (event) {
    case 'trace':
      handlers.onTrace?.(data as TraceStep)
      break
    case 'sources':
      handlers.onSources?.(data as Source[])
      break
    case 'token':
      handlers.onToken?.((data as { t?: string }).t ?? '')
      break
    case 'done':
      handlers.onDone?.(data as DonePayload)
      break
    case 'error':
      handlers.onError?.((data as { message?: string }).message ?? 'Unknown server error')
      break
    default:
      break
  }
}
