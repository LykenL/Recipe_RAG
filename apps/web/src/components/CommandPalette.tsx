import { useEffect, useRef, useState } from 'react'
import { fetchRecipes } from '../lib/api'
import type { RecipeSummary } from '../lib/types'
import { Search } from './icons'

interface Props {
  open: boolean
  onClose: () => void
  onOpenRecipe: (dish: RecipeSummary) => void
  onAsk: (dish: RecipeSummary) => void
}

/**
 * ⌘K palette — direct search over the index.
 *
 * This is the only entry point that does not touch the model, so it keeps
 * working while an answer is queued, rate-limited or the quota is exhausted.
 */
export function CommandPalette({ open, onClose, onOpenRecipe, onAsk }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<RecipeSummary[]>([])
  const [cursor, setCursor] = useState(0)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // reset each time it opens
  useEffect(() => {
    if (!open) return
    setQuery('')
    setCursor(0)
    setResults([])
    window.setTimeout(() => inputRef.current?.focus(), 30)
  }, [open])

  useEffect(() => {
    if (!open) return
    const t = window.setTimeout(() => {
      setLoading(true)
      fetchRecipes({ q: query.trim(), pageSize: 8 })
        .then((d) => {
          setResults(d.items)
          setCursor(0)
        })
        .catch(() => setResults([]))
        .finally(() => setLoading(false))
    }, query ? 180 : 0)
    return () => window.clearTimeout(t)
  }, [query, open])

  // keep the highlighted row in view
  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>('.cmdk-row.on')?.scrollIntoView({ block: 'nearest' })
  }, [cursor])

  if (!open) return null

  const choose = (dish: RecipeSummary, ask: boolean) => {
    onClose()
    if (ask) onAsk(dish)
    else onOpenRecipe(dish)
  }

  return (
    <>
      <button className="scrim" aria-label="Close search" onClick={onClose} />
      <div className="cmdk" role="dialog" aria-modal="true" aria-label="Search recipes">
        <div className="cmdk-input">
          <Search width={16} height={16} />
          <input
            ref={inputRef}
            value={query}
            placeholder="Search 829 recipes…"
            aria-label="Search recipes"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.preventDefault()
                onClose()
              } else if (e.key === 'ArrowDown') {
                e.preventDefault()
                setCursor((c) => Math.min(c + 1, results.length - 1))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setCursor((c) => Math.max(c - 1, 0))
              } else if (e.key === 'Enter' && results[cursor]) {
                e.preventDefault()
                choose(results[cursor], e.metaKey || e.ctrlKey)
              }
            }}
          />
          <kbd>esc</kbd>
        </div>

        <div className="cmdk-list" ref={listRef}>
          {loading && results.length === 0 && <div className="cmdk-empty">Searching…</div>}
          {!loading && results.length === 0 && (
            <div className="cmdk-empty">
              {query ? `Nothing matches “${query}”.` : 'Type to search the cookbook.'}
            </div>
          )}
          {results.map((d, i) => (
            <button
              key={d.id}
              className={`cmdk-row${i === cursor ? ' on' : ''}`}
              onMouseEnter={() => setCursor(i)}
              onClick={(e) => choose(d, e.metaKey || e.ctrlKey)}
            >
              {d.image ? (
                <img src={d.image} alt="" loading="lazy" decoding="async" />
              ) : (
                <span className="cmdk-noimg">{d.title.slice(0, 1)}</span>
              )}
              <span className="cmdk-text">
                <span className="cmdk-title">{d.title}</span>
                <span className="cmdk-sub">
                  {[d.area, d.category].filter(Boolean).join(' · ') || 'cookbook'}
                </span>
              </span>
              {typeof d.score === 'number' && <span className="cmdk-score">{d.score.toFixed(2)}</span>}
            </button>
          ))}
        </div>

        <div className="cmdk-foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open recipe</span>
          <span><kbd>⌘</kbd>+<kbd>↵</kbd> ask the chef</span>
        </div>
      </div>
    </>
  )
}
