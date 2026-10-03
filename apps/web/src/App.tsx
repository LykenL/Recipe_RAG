import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { BrowseView } from './components/BrowseView'
import { ChatThread } from './components/ChatThread'
import { CommandPalette } from './components/CommandPalette'
import { RecipeDetail } from './components/RecipeDetail'
import { Composer } from './components/Composer'
import { EmptyState } from './components/EmptyState'
import { Sidebar } from './components/Sidebar'
import { SourceDrawer } from './components/SourceDrawer'
import { TopBar } from './components/TopBar'
import { fetchIndexInfo, fetchSamples } from './lib/api'
import type { IndexInfo, KitchenSettings, RecipeSummary, SampleDish } from './lib/types'
import { useChat } from './hooks/useChat'
import { useSessions } from './hooks/useSessions'
import { useBrowse } from './hooks/useBrowse'

const DEFAULT_SETTINGS: KitchenSettings = {
  persona: 'Friendly home cook',
  dietary: [],
  pantry: [],
}

export default function App() {
  const [settings, setSettings] = useState<KitchenSettings>(DEFAULT_SETTINGS)
  const [info, setInfo] = useState<IndexInfo | null>(null)
  const [samples, setSamples] = useState<SampleDish[]>([])
  const [online, setOnline] = useState(true)
  const [waking, setWaking] = useState(false)
  const [railOpen, setRailOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [view, setView] = useState<'chat' | 'browse'>('chat')
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [detail, setDetail] = useState<RecipeSummary | null>(null)

  const { messages, streaming, sources, send, stop, load } = useChat()
  const sessions = useSessions()
  const scrollRef = useRef<HTMLDivElement>(null)
  const loadedRef = useRef<string | null>(null)
  const browse = useBrowse(view === 'browse')

  useEffect(() => {
    const ctrl = new AbortController()
    fetchIndexInfo(ctrl.signal)
      .then((data) => {
        setInfo(data)
        setOnline(true)
      })
      .catch(() => setOnline(false))
    // The browse strip is decorative until asked for; never block first paint.
    fetchSamples(6, ctrl.signal)
      .then(setSamples)
      .catch(() => setSamples([]))
    return () => ctrl.abort()
  }, [])

  // ⌘K / Ctrl+K opens the index search from anywhere.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((open) => !open)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // A free Render instance is evicted after ~15 min idle; the next request pays
  // the whole boot. Say so rather than showing a dead "connecting…".
  useEffect(() => {
    if (info) {
      setWaking(false)
      return
    }
    const t = window.setTimeout(() => setWaking(true), 4000)
    return () => window.clearTimeout(t)
  }, [info])

  // Swap the transcript when the active conversation changes.
  useEffect(() => {
    const active = sessions.active
    if (!active || loadedRef.current === active.id) return
    loadedRef.current = active.id
    load(active.messages)
  }, [sessions.active, load])

  // Persist after the tokens stop arriving, not on every one of them.
  useEffect(() => {
    const id = sessions.activeId
    if (!id || loadedRef.current !== id) return
    const t = window.setTimeout(() => sessions.store(id, messages), 700)
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, sessions.activeId])

  // Keep the newest turn in view while tokens stream in.
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 220
    if (nearBottom || streaming) el.scrollTop = el.scrollHeight
  }, [messages, streaming])

  const handleSend = useCallback(
    (text: string) => {
      setDrawerOpen(false)
      void send(text, settings)
    },
    [send, settings],
  )

  /** Hand a dish to the agent — the one path where browsing leads to the chat. */
  const askAbout = useCallback(
    (dish: RecipeSummary) => {
      setDetail(null)
      setPaletteOpen(false)
      setView('chat')
      handleSend(`How do I make ${dish.title}?`)
    },
    [handleSend],
  )

  const tags = useMemo(() => {
    const t = settings.dietary.map((d) => (d === 'Nut allergy' ? 'Nut-free' : d))
    if (settings.pantry.length > 0) t.push(`Using ${settings.pantry.length} pantry items`)
    return t
  }, [settings])

  const history = useMemo(
    () => messages.filter((m) => m.role === 'user').map((m) => m.content),
    [messages],
  )

  const lastUser = history.length > 0 ? history[history.length - 1] : null
  const title = lastUser ? lastUser.slice(0, 60) : 'New conversation'
  const answered = messages.filter((m) => m.role === 'assistant' && m.done).length
  const subtitle =
    history.length === 0
      ? 'Nothing asked yet'
      : `${history.length} question${history.length === 1 ? '' : 's'} · ${answered} answered`

  const isEmpty = messages.length === 0

  return (
    <div className={`app${sources.length > 0 ? ' with-drawer' : ''}`}>
      <Sidebar
        settings={settings}
        onChange={setSettings}
        info={info}
        sessions={sessions.sessions}
        activeId={sessions.activeId}
        onNewChat={() => {
          sessions.create()
          setRailOpen(false)
        }}
        onSelectSession={sessions.select}
        onDeleteSession={sessions.remove}
        open={railOpen}
        onClose={() => setRailOpen(false)}
      />

      <main className={`canvas${isEmpty ? ' empty' : ''}`}>
        <TopBar
          title={title}
          subtitle={subtitle}
          info={info}
          online={online}
          waking={waking}
          sourceCount={sources.length}
          view={view}
          onView={setView}
          onSearch={() => setPaletteOpen(true)}
          onOpenSettings={() => setRailOpen(true)}
          onToggleSources={() => setDrawerOpen((v) => !v)}
        />

        <div className="scroll" ref={scrollRef}>
          <div className={`wrap${view === 'browse' ? ' wide' : ''}`}>
            {view === 'browse' ? (
              <BrowseView
                items={browse.items}
                total={browse.total}
                hasMore={browse.hasMore}
                loading={browse.loading}
                loadingMore={browse.loadingMore}
                error={browse.error}
                query={browse.query}
                category={browse.category}
                area={browse.area}
                facets={browse.facets}
                onQuery={browse.setQuery}
                onCategory={browse.setCategory}
                onArea={browse.setArea}
                onLoadMore={browse.loadMore}
                onOpen={setDetail}
                onAsk={askAbout}
              />
            ) : isEmpty ? (
              <EmptyState
                onSend={handleSend}
                onStop={stop}
                streaming={streaming}
                tags={tags}
                samples={samples}
              />
            ) : (
              <ChatThread
                messages={messages}
                pantry={settings.pantry}
                dietary={settings.dietary}
              />
            )}
          </div>
        </div>

        {view === 'chat' && !isEmpty && (
          <div className="dock">
            <div className="wrap">
              {!online && (
                <div className="copy-error">
                  Can’t reach the API — check that the backend is running and the index loaded.
                </div>
              )}
              <Composer
                variant="docked"
                onSend={handleSend}
                onStop={stop}
                streaming={streaming}
                autoFocus
              />
            </div>
          </div>
        )}
      </main>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onOpenRecipe={setDetail}
        onAsk={askAbout}
      />

      <RecipeDetail dish={detail} onClose={() => setDetail(null)} onAsk={askAbout} />

      {view === 'chat' && sources.length > 0 && (
        <SourceDrawer
          sources={sources}
          info={info}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          dietary={settings.dietary}
        />
      )}
    </div>
  )
}
