import type { IndexInfo } from '../lib/types'
import { Book, Menu, Search } from './icons'

interface Props {
  title: string
  subtitle: string
  info: IndexInfo | null
  online: boolean
  /** true when the first request has been pending long enough to look stuck */
  waking: boolean
  sourceCount: number
  view: 'chat' | 'browse'
  onView: (v: 'chat' | 'browse') => void
  onSearch: () => void
  onOpenSettings: () => void
  onToggleSources: () => void
}

export function TopBar({
  title,
  subtitle,
  info,
  online,
  waking,
  sourceCount,
  view,
  onView,
  onSearch,
  onOpenSettings,
  onToggleSources,
}: Props) {
  return (
    <header className="topbar">
      <button className="iconbtn rail-toggle" onClick={onOpenSettings} aria-label="Open settings">
        <Menu width={16} height={16} />
      </button>

      <nav className="viewtabs" aria-label="View">
        <button className={view === 'chat' ? 'on' : ''} onClick={() => onView('chat')}>
          Chat
        </button>
        <button className={view === 'browse' ? 'on' : ''} onClick={() => onView('browse')}>
          Browse
        </button>
      </nav>

      {view === 'chat' && (
        <div style={{ minWidth: 0, marginLeft: 4 }}>
          <div className="tb-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {title}
          </div>
          <div className="tb-sub">{subtitle}</div>
        </div>
      )}

      <div className="tb-right">
        <button className="searchbtn" onClick={onSearch} title="Search the cookbook (⌘K)">
          <Search width={13} height={13} />
          <span>Search</span>
          <kbd>⌘K</kbd>
        </button>
        <span
          className="pill"
          title={
            !online ? 'API unreachable' : waking ? 'Free instance starting up' : 'API reachable'
          }
        >
          <span className={`dot${online ? (waking ? ' busy' : '') : ' bad'}`} />
          {info
            ? `${info.count.toLocaleString()} recipes`
            : waking
              ? 'waking the server…'
              : 'connecting…'}
        </span>
        {view === 'chat' && (
        <button className="iconbtn drawer-toggle" onClick={onToggleSources} aria-label="Toggle sources">
          <Book width={15} height={15} />
          {sourceCount > 0 && (
            <span
              style={{
                position: 'absolute',
                marginLeft: 18,
                marginTop: -14,
                background: 'var(--terra)',
                color: '#fff',
                borderRadius: 999,
                font: '600 9px/1 var(--ui)',
                padding: '3px 4px',
              }}
            >
              {sourceCount}
            </span>
          )}
        </button>
        )}
      </div>
    </header>
  )
}
