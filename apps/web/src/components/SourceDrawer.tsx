import type { IndexInfo, Source } from '../lib/types'
import { Book, X } from './icons'

interface Props {
  sources: Source[]
  info: IndexInfo | null
  open: boolean
  onClose: () => void
}

export function SourceDrawer({ sources, info, open, onClose }: Props) {
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
          Every sentence in the answer resolves to one of these passages. Scores are cosine
          similarity against your question.
        </div>

        <div className="drawer-body">
          {sources.length === 0 ? (
            <div className="drawer-empty">
              No passages retrieved yet.
              <br />
              Ask a cooking question and the matches will appear here.
            </div>
          ) : (
            sources.map((s, i) => (
              <article className="src" key={`${s.title}-${i}`}>
                <div className="src-top">
                  <span className="idx">{i + 1}</span>
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
                {s.snippet && <p>“{s.snippet}”</p>}
              </article>
            ))
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
