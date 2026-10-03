import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchRecipes } from '../lib/api'
import type { Facet, RecipeSummary } from '../lib/types'

const PAGE_SIZE = 24

export interface BrowseState {
  items: RecipeSummary[]
  total: number
  hasMore: boolean
  loading: boolean
  loadingMore: boolean
  error: string | null
  query: string
  category: string
  area: string
  facets: { category: Facet[]; area: Facet[] }
  setQuery: (q: string) => void
  setCategory: (c: string) => void
  setArea: (a: string) => void
  loadMore: () => void
}

/**
 * Paged cookbook browsing.
 *
 * Typing is debounced because every keystroke is an embedding pass over the
 * index; it is only ~1ms, but it still should not fire 12 times per word.
 */
export function useBrowse(active: boolean): BrowseState {
  const [items, setItems] = useState<RecipeSummary[]>([])
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [category, setCategory] = useState('')
  const [area, setArea] = useState('')
  const [facets, setFacets] = useState<BrowseState['facets']>({ category: [], area: [] })

  const pageRef = useRef(1)
  const reqRef = useRef(0)

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(query.trim()), 250)
    return () => window.clearTimeout(t)
  }, [query])

  // first page whenever the filters change
  useEffect(() => {
    if (!active) return
    const token = ++reqRef.current
    setLoading(true)
    setError(null)
    fetchRecipes({ q: debounced, category, area, page: 1, pageSize: PAGE_SIZE })
      .then((data) => {
        if (token !== reqRef.current) return // a newer request already won
        setItems(data.items)
        setTotal(data.total)
        setHasMore(data.has_more)
        setFacets(data.facets)
        pageRef.current = 1
      })
      .catch((e: Error) => {
        if (token === reqRef.current) setError(e.message)
      })
      .finally(() => {
        if (token === reqRef.current) setLoading(false)
      })
  }, [active, debounced, category, area])

  const loadMore = useCallback(() => {
    if (loading || loadingMore || !hasMore) return
    const next = pageRef.current + 1
    const token = ++reqRef.current
    setLoadingMore(true)
    fetchRecipes({ q: debounced, category, area, page: next, pageSize: PAGE_SIZE })
      .then((data) => {
        if (token !== reqRef.current) return
        setItems((prev) => [...prev, ...data.items])
        setHasMore(data.has_more)
        pageRef.current = next
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingMore(false))
  }, [loading, loadingMore, hasMore, debounced, category, area])

  return {
    items, total, hasMore, loading, loadingMore, error,
    query, category, area, facets,
    setQuery, setCategory, setArea, loadMore,
  }
}
