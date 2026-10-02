import type { IndexInfo } from '../lib/types'
import { Book, Menu } from './icons'

interface Props {
  title: string
  subtitle: string
  info: IndexInfo | null
  online: boolean
  sourceCount: number
  onOpenSettings: () => void
  onToggleSources: () => void
}

export function TopBar({
  title,
  subtitle,
  info,
  online,
  sourceCount,
  onOpenSettings,
  onToggleSources,
}: Props) {
  return (
    <header className="topbar">
      <button className="iconbtn rail-toggle" onClick={onOpenSettings} aria-label="Open settings">
        <Menu width={16} height={16} />
      </button>

      <div style={{ minWidth: 0 }}>
        <div className="tb-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {title}
        </div>
        <div className="tb-sub">{subtitle}</div>
      </div>

      <div className="tb-right">
        <span className="pill" title={online ? 'API reachable' : 'API unreachable'}>
          <span className={`dot${online ? '' : ' bad'}`} />
          {info ? `${info.count.toLocaleString()} recipes` : 'connecting…'}
        </span>
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
      </div>
    </header>
  )
}
