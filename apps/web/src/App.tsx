import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ChatThread } from './components/ChatThread'
import { Composer } from './components/Composer'
import { EmptyState } from './components/EmptyState'
import { Sidebar } from './components/Sidebar'
import { SourceDrawer } from './components/SourceDrawer'
import { TopBar } from './components/TopBar'
import { fetchIndexInfo, fetchSamples } from './lib/api'
import type { IndexInfo, KitchenSettings, SampleDish } from './lib/types'
import { useChat } from './hooks/useChat'
import { useSessions } from './hooks/useSessions'

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

  const { messages, streaming, sources, send, stop, load } = useChat()
  const sessions = useSessions()
  const scrollRef = useRef<HTMLDivElement>(null)
  const loadedRef = useRef<string | null>(null)

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
          onOpenSettings={() => setRailOpen(true)}
          onToggleSources={() => setDrawerOpen((v) => !v)}
        />

        <div className="scroll" ref={scrollRef}>
          <div className="wrap">
            {isEmpty ? (
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

        {!isEmpty && (
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

      {sources.length > 0 && (
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
