import { useEffect, useState } from 'react'
import type { TraceStep } from '../lib/types'
import { Check, Dots, Filter, Search, Shield, Whisk } from './icons'

interface Props {
  steps: TraceStep[]
  pending: boolean
  elapsedMs?: number
  /** the dietary settings this answer was asked under */
  restrictions?: string[]
}

/**
 * Renders the agent's retrieval steps as they arrive over SSE.
 *
 * The point of this component is auditability: a reader should be able to see
 * that an answer came from a search over N recipes, not from the model's
 * imagination. That is why the search query and hit count are shown verbatim.
 *
 * While pending it also runs a live clock: on the free tier one answer can take
 * anywhere from 10s to over two minutes, and a frozen "Composing…" for that long
 * reads as a hung request.
 */
export function AgentTrace({ steps, pending, elapsedMs, restrictions = [] }: Props) {
  const [liveSeconds, setLiveSeconds] = useState(0)

  useEffect(() => {
    if (!pending) return
    const started = Date.now()
    setLiveSeconds(0)
    const id = window.setInterval(
      () => setLiveSeconds(Math.round((Date.now() - started) / 1000)),
      500,
    )
    return () => window.clearInterval(id)
  }, [pending])

  const searches = steps.filter((s) => s.step === 'search')
  const total = steps.length + (pending ? 1 : 0)
  const clock = pending
    ? `${liveSeconds}s`
    : elapsedMs != null
      ? `${(elapsedMs / 1000).toFixed(1)} s`
      : undefined

  return (
    <div className="trace">
      <div className="trace-head">
        <Whisk width={14} height={14} style={{ color: 'var(--terra)' }} />
        Agent trace
        <span className="sp">
          {total} step{total === 1 ? '' : 's'}
          {clock && ` · ${clock}`}
        </span>
      </div>

      {restrictions.length > 0 && (
        <div className="step">
          <span className="s-ic" style={{ background: 'var(--terra-soft)', color: 'var(--terra)' }}>
            <Shield width={11} height={11} />
          </span>
          Asked under your restrictions
          <span className="s-meta">{restrictions.join(' · ')}</span>
        </div>
      )}

      {steps.map((step, i) => {
        if (step.step === 'search') {
          const n = step.hits ?? step.sources?.length ?? 0
          return (
            <div className="step" key={i}>
              <span className="s-ic"><Search width={11} height={11} /></span>
              Searched <code>{step.query}</code> — {n} match{n === 1 ? '' : 'es'}
              {step.ms != null && <span className="s-meta">{step.ms} ms</span>}
            </div>
          )
        }
        return (
          <div className="step" key={i}>
            <span className="s-ic"><Check width={11} height={11} /></span>
            {step.label ?? step.step}
            {step.ms != null && <span className="s-meta">{step.ms} ms</span>}
          </div>
        )
      })}

      {pending && (
        <div className="step run">
          <span className="s-ic pulse">
            {searches.length === 0 ? <Search width={11} height={11} /> : <Dots width={11} height={11} />}
          </span>
          {searches.length === 0 ? 'Searching the cookbook…' : 'Composing the answer…'}
          <span className="s-meta">{liveSeconds}s</span>
        </div>
      )}

      {pending && liveSeconds >= 25 && (
        <div className="step">
          <span className="s-ic" style={{ background: 'var(--terra-soft)', color: 'var(--terra)' }}>
            <Dots width={11} height={11} />
          </span>
          Still working — the free model tier can queue for up to a minute.
        </div>
      )}

      {!pending && searches.length === 0 && steps.length > 0 && (
        <div className="step">
          <span className="s-ic" style={{ background: 'var(--surface-2)', color: 'var(--faint)' }}>
            <Filter width={11} height={11} />
          </span>
          No cookbook search was needed for this question
        </div>
      )}
    </div>
  )
}
