import { useEffect, useState } from 'react'
import { fetchRecipe } from '../lib/api'
import type { RecipeDetail as Detail, RecipeSummary } from '../lib/types'
import { Book, Sparkle, X } from './icons'

interface Props {
  dish: RecipeSummary | null
  onClose: () => void
  onAsk: (dish: RecipeSummary) => void
}

/** Full recipe text, straight from the index — no model, no streaming. */
export function RecipeDetail({ dish, onClose, onAsk }: Props) {
  const [detail, setDetail] = useState<Detail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!dish) {
      setDetail(null)
      return
    }
    const ctrl = new AbortController()
    setDetail(null)
    setError(null)
    fetchRecipe(dish.id, ctrl.signal)
      .then(setDetail)
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError(e.message)
      })
    return () => ctrl.abort()
  }, [dish])

  useEffect(() => {
    if (!dish) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [dish, onClose])

  if (!dish) return null

  const servings = Array.isArray(detail?.serving_size) && detail.serving_size[1] > 0
    ? `Serves ${detail.serving_size[0]}–${detail.serving_size[1]}`
    : null

  return (
    <>
      <button className="scrim" aria-label="Close recipe" onClick={onClose} />
      <aside className="detail" role="dialog" aria-modal="true" aria-label={dish.title}>
        <div className="detail-head">
          <Book width={15} height={15} />
          <h3>Recipe</h3>
          <button className="iconbtn" style={{ marginLeft: 'auto' }} onClick={onClose} aria-label="Close">
            <X width={13} height={13} />
          </button>
        </div>

        {dish.image && (
          <div className="detail-photo" style={{ backgroundImage: `url("${dish.image}")` }} />
        )}

        <div className="detail-body">
          <h2 className="detail-title">{dish.title}</h2>
          <div className="detail-meta">
            {[dish.area, dish.category].filter(Boolean).join(' · ')}
            {servings && ` · ${servings}`}
          </div>

          {error && <div className="copy-error">{error}</div>}
          {!detail && !error && <div className="detail-loading">Loading…</div>}

          {detail && (
            <>
              {detail.ingredients && (
                <>
                  <div className="detail-lbl">Ingredients</div>
                  <ul className="detail-list">
                    {detail.ingredients
                      .split('\n')
                      .map((l) => l.trim())
                      .filter(Boolean)
                      .map((l, i) => (
                        <li key={i}>{l.replace(/^[-•*]\s*/, '')}</li>
                      ))}
                  </ul>
                </>
              )}
              {detail.instructions && (
                <>
                  <div className="detail-lbl">Method</div>
                  <div className="detail-steps">
                    {detail.instructions
                      .split(/\n|(?=\bstep \d)/i)
                      .map((l) => l.trim())
                      .filter(Boolean)
                      .map((l, i) => (
                        <p key={i}>{l}</p>
                      ))}
                  </div>
                </>
              )}
              {detail.notes && <div className="detail-note">{detail.notes}</div>}
            </>
          )}
        </div>

        <div className="detail-foot">
          <button className="btn" onClick={() => onAsk(dish)} style={{ width: '100%', justifyContent: 'center' }}>
            <Sparkle width={14} height={14} /> Ask the chef about this
          </button>
        </div>
      </aside>
    </>
  )
}
