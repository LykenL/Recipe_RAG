import type { RecipeSummary } from '../lib/types'
import { Search } from './icons'

interface Props {
  items: RecipeSummary[]
  total: number
  hasMore: boolean
  loading: boolean
  loadingMore: boolean
  error: string | null
  query: string
  category: string
  area: string
  facets: { category: { value: string; count: number }[]; area: { value: string; count: number }[] }
  onQuery: (q: string) => void
  onCategory: (c: string) => void
  onArea: (a: string) => void
  onLoadMore: () => void
  onOpen: (dish: RecipeSummary) => void
  onAsk: (dish: RecipeSummary) => void
}

export function BrowseView({
  items, total, hasMore, loading, loadingMore, error,
  query, category, area, facets,
  onQuery, onCategory, onArea, onLoadMore, onOpen, onAsk,
}: Props) {
  const withPhotos = items.filter((i) => i.image).length

  return (
    <div className="browse-view">
      <div className="browse-head">
        <span className="eyebrow">Straight from the index · no model involved</span>
        <h1 className="browse-title">The cookbook</h1>
        <p className="lede" style={{ fontSize: 15 }}>
          {total.toLocaleString()} dishes
          {items.length > 0 && ` · ${withPhotos} of the first ${items.length} have photos`}. Browsing
          reads the same index the agent searches, so it stays instant even when the model is queued.
        </p>
      </div>

      <div className="browse-controls">
        <label className="browse-search">
          <Search width={14} height={14} />
          <input
            value={query}
            placeholder="Search dishes — “chocolate”, “piri-piri”, “dumplings”…"
            aria-label="Search dishes"
            onChange={(e) => onQuery(e.target.value)}
          />
          {query && (
            <button className="browse-clear" onClick={() => onQuery('')} aria-label="Clear search">
              ×
            </button>
          )}
        </label>
        <select
          className="browse-area"
          value={area}
          aria-label="Filter by region"
          onChange={(e) => onArea(e.target.value)}
        >
          <option value="">All regions</option>
          {facets.area.map((f) => (
            <option key={f.value} value={f.value}>
              {f.value} ({f.count})
            </option>
          ))}
        </select>
      </div>

      <div className="browse-cats">
        <button
          className={`catchip${category === '' ? ' on' : ''}`}
          onClick={() => onCategory('')}
        >
          All
        </button>
        {facets.category.map((f) => (
          <button
            key={f.value}
            className={`catchip${category === f.value ? ' on' : ''}`}
            onClick={() => onCategory(category === f.value ? '' : f.value)}
          >
            {f.value} <span>{f.count}</span>
          </button>
        ))}
      </div>

      {error && <div className="copy-error">{error}</div>}

      {loading ? (
        <div className="browse-grid">
          {Array.from({ length: 12 }).map((_, i) => (
            <div className="dish-skel" key={i} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="browse-empty">
          Nothing matched{query && ` “${query}”`}
          {category && ` in ${category}`}. Try a different word.
        </div>
      ) : (
        <>
          <div className="browse-grid">
            {items.map((d) => (
              <article className="dish-card" key={d.id}>
                <button className="dish-open" onClick={() => onOpen(d)} title={`Open ${d.title}`}>
                  {d.image ? (
                    <img src={d.image} alt="" loading="lazy" decoding="async" />
                  ) : (
                    <span className="dish-noimg">{d.title.slice(0, 1)}</span>
                  )}
                  <span className="cap">
                    <h5>{d.title}</h5>
                    <span>{[d.area, d.category].filter(Boolean).join(' · ') || 'cookbook'}</span>
                  </span>
                  {typeof d.score === 'number' && (
                    <span className="dish-score">{d.score.toFixed(2)}</span>
                  )}
                </button>
                <button className="dish-ask" onClick={() => onAsk(d)} title={`Ask the chef about ${d.title}`}>
                  Ask the chef
                </button>
              </article>
            ))}
          </div>

          {hasMore && (
            <div className="browse-more">
              <button className="btn ghost" onClick={onLoadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading…' : `Load more (${(total - items.length).toLocaleString()} left)`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
