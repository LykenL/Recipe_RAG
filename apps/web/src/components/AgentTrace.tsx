import type { TraceStep } from '../lib/types'
import { Check, Dots, Filter, Search, Sparkle } from './icons'

interface Props {
  steps: TraceStep[]
  pending: boolean
  elapsedMs?: number
}

/**
 * Renders the agent's retrieval steps as they arrive over SSE.
 *
 * The point of this component is auditability: a reader should be able to see
 * that an answer came from a search over N recipes, not from the model's
 * imagination. That is why the search query and hit count are shown verbatim.
 */
export function AgentTrace({ steps, pending, elapsedMs }: Props) {
  const searches = steps.filter((s) => s.step === 'search')
  const total = steps.length + (pending ? 1 : 0)

  return (
    <div className="trace">
      <div className="trace-head">
        <Sparkle width={14} height={14} style={{ color: 'var(--terra)' }} />
        Agent trace
        <span className="sp">
          {total} step{total === 1 ? '' : 's'}
          {elapsedMs != null && ` · ${(elapsedMs / 1000).toFixed(1)} s`}
        </span>
      </div>

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
