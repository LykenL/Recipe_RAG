import { useState } from 'react'
import type { IndexInfo, Source } from '../lib/types'
import { Book, Chevron, X } from './icons'

interface Props {
  sources: Source[]
  info: IndexInfo | null
  open: boolean
  onClose: () => void
}

export function SourceDrawer({ sources, info, open, onClose }: Props) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const best = sources.length > 0 ? Math.max(...sources.map((s) => s.score)) : 1

  return (
    <>
      {open && <button className="scrim" aria-label="Close sources" onClick={onClose} />}
      <aside className={`drawer${open ? ' open' : ''}`} aria-label="Retrieved sources">
        <div className="drawer-head">
          <Book width={15} height={15} />
          <h3>Sources</h3>
          {sources.length > 0 && <span className="badge">{sources.length} retrieved</span>}
          <button className="iconbtn drawer-toggle" style={{ marginLeft: 'auto' }} onClick={onClose} aria-label="Close">
            <X width={13} height={13} />
          </button>
        </div>

        <div className="drawer-note">
          Every sentence in the answer resolves to one of these passages. Click a card to read
          the full passage — that is how you check the answer against its source.
        </div>

        <div className="drawer-body">
          {sources.length === 0 ? (
            <div className="drawer-empty">
              No passages retrieved yet.
              <br />
              Ask a cooking question and the matches will appear here.
            </div>
          ) : (
            sources.map((s, i) => {
              const body = s.full_text || s.snippet
              const canExpand = body.length > (s.snippet?.length ?? 0) + 20
              const isOpen = Boolean(expanded[i])
              return (
                <article
                  className={`src${canExpand ? ' expandable' : ''}`}
                  key={`${s.title}-${i}`}
                  onClick={() => canExpand && setExpanded((p) => ({ ...p, [i]: !p[i] }))}
                  role={canExpand ? 'button' : undefined}
                  tabIndex={canExpand ? 0 : undefined}
                  aria-expanded={canExpand ? isOpen : undefined}
                  onKeyDown={(e) => {
                    if (canExpand && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault()
                      setExpanded((p) => ({ ...p, [i]: !p[i] }))
                    }
                  }}
                >
                  <div className="src-top">
                    <div className="src-thumb">
                      {s.image ? (
                        <img src={s.image} alt="" loading="lazy" decoding="async" />
                      ) : (
                        <span className="fallback">{s.title.slice(0, 1)}</span>
                      )}
                      <span className="src-idx">{i + 1}</span>
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <h4>{s.title}</h4>
                      <div className="sub">
                        {[s.area, s.category].filter(Boolean).join(' · ') || s.source || 'cookbook'}
                      </div>
                    </div>
                    <div className="score">
                      <b>{s.score.toFixed(2)}</b>
                    </div>
                  </div>
                  {/* bars are scaled to the best hit so small differences stay visible */}
                  <div className="bar">
                    <i style={{ width: `${Math.max(6, (s.score / best) * 100)}%` }} />
                  </div>
                  <p className={isOpen ? 'full' : ''}>{isOpen ? body : body.slice(0, 220)}</p>
                  {canExpand && (
                    <span className="src-toggle">
                      {isOpen ? 'Show less' : 'Show full passage'}
                      <Chevron width={12} height={12} style={{ transform: isOpen ? 'rotate(180deg)' : undefined }} />
                    </span>
                  )}
                </article>
              )
            })
          )}
        </div>

        {info && (
          <div className="drawer-foot">
            Index: {info.count.toLocaleString()} recipes · dim {info.dim}
            <br />
            {info.model} · {info.backend} · k={info.k} · ≥{info.min_similarity}
          </div>
        )}
      </aside>
    </>
  )
}
