import { useState } from 'react'
import type { Session } from '../lib/sessions'
import type { IndexInfo, KitchenSettings } from '../lib/types'
import { ChefHat, Chevron, Plus, X } from './icons'

export const PERSONAS = [
  'Friendly home cook',
  'Gordon Ramsay (harsh & pro)',
  'Nutritionist (health-focused)',
] as const

export const DIETARY = ['Vegetarian', 'Gluten-free', 'Nut allergy', 'Dairy-free'] as const

const SUGGESTED_PANTRY = [
  'Chicken', 'Eggs', 'Milk', 'Butter', 'Garlic', 'Onion',
  'Tomatoes', 'Spinach', 'Lemon', 'Rice', 'Pasta', 'Cheese',
]

interface Props {
  settings: KitchenSettings
  onChange: (next: KitchenSettings) => void
  info: IndexInfo | null
  sessions: Session[]
  activeId: string | null
  onNewChat: () => void
  onSelectSession: (id: string) => void
  onDeleteSession: (id: string) => void
  open: boolean
  onClose: () => void
}

const relativeDay = (ts: number): string => {
  const days = Math.floor((Date.now() - ts) / 86_400_000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days}d ago`
  return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function Sidebar({
  settings,
  onChange,
  info,
  sessions,
  activeId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  open,
  onClose,
}: Props) {
  const [draft, setDraft] = useState('')

  const toggleDietary = (name: string) =>
    onChange({
      ...settings,
      dietary: settings.dietary.includes(name)
        ? settings.dietary.filter((d) => d !== name)
        : [...settings.dietary, name],
    })

  const addPantry = (raw: string) => {
    const item = raw.trim().replace(/,$/, '')
    if (!item) return
    if (!settings.pantry.some((p) => p.toLowerCase() === item.toLowerCase())) {
      onChange({ ...settings, pantry: [...settings.pantry, item] })
    }
    setDraft('')
  }

  const removePantry = (item: string) =>
    onChange({ ...settings, pantry: settings.pantry.filter((p) => p !== item) })

  return (
    <aside className={`rail${open ? ' open' : ''}`} aria-label="Kitchen settings">
      <div className="brand">
        <div className="mark">
          <ChefHat width={17} height={17} />
        </div>
        <div>
          <div className="brand-name">Mise</div>
          <div className="brand-sub">Recipe agent</div>
        </div>
        <button
          className="iconbtn rail-toggle"
          style={{ marginLeft: 'auto' }}
          onClick={onClose}
          aria-label="Close settings"
        >
          <X width={13} height={13} />
        </button>
      </div>

      <button className="newchat" onClick={onNewChat}>
        <Plus width={14} height={14} /> New chat
      </button>

      <div>
        <div className="rail-h">Chef persona</div>
        <div className="field">
          <select
            value={settings.persona}
            aria-label="Chef persona"
            onChange={(e) => onChange({ ...settings, persona: e.target.value })}
          >
            {PERSONAS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <Chevron width={13} height={13} />
        </div>
      </div>

      <div>
        <div className="rail-h">Dietary</div>
        {DIETARY.map((name) => {
          const isAllergy = name === 'Nut allergy'
          const on = settings.dietary.includes(name)
          return (
            <label className="switch-row" key={name}>
              <span>{name}</span>
              <button
                type="button"
                role="switch"
                aria-checked={on}
                aria-label={name}
                className={`sw${on ? ' on' : ''}${isAllergy ? ' terra' : ''}`}
                onClick={(e) => {
                  e.preventDefault()
                  toggleDietary(name)
                }}
              />
            </label>
          )
        })}
      </div>

      <div>
        <div className="rail-h">In my pantry</div>
        <div className="chips">
          {settings.pantry.map((item) => (
            <span className="chip" key={item}>
              {item}
              <button
                className="x"
                onClick={() => removePantry(item)}
                aria-label={`Remove ${item}`}
                style={{ background: 'none', padding: 0 }}
              >
                ×
              </button>
            </span>
          ))}
          {settings.pantry.length === 0 && (
            <span style={{ font: '400 12.5px/1.5 var(--ui)', color: 'var(--muted)' }}>
              Nothing yet — add what you have.
            </span>
          )}
        </div>

        <form
          className="pantry-add"
          onSubmit={(e) => {
            e.preventDefault()
            addPantry(draft)
          }}
        >
          <input
            value={draft}
            list="pantry-suggestions"
            placeholder="Add an ingredient…"
            aria-label="Add an ingredient"
            onChange={(e) => setDraft(e.target.value)}
          />
          <datalist id="pantry-suggestions">
            {SUGGESTED_PANTRY.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
          <button type="submit" aria-label="Add ingredient">
            <Plus width={13} height={13} />
          </button>
        </form>
      </div>

      <div>
        <div className="rail-h">
          Conversations
          <span style={{ float: 'right', fontWeight: 500, letterSpacing: 0, textTransform: 'none' }}>
            {sessions.length}
          </span>
        </div>
        <div className="recent">
          {sessions.map((s) => {
            const isActive = s.id === activeId
            const preview =
              s.messages.find((m) => m.role === 'assistant' && m.done)?.done?.citations ?? 0
            return (
              <div className={`ritem-wrap${isActive ? ' on' : ''}`} key={s.id}>
                <button
                  className={`ritem${isActive ? ' on' : ''}`}
                  onClick={() => {
                    onSelectSession(s.id)
                    onClose()
                  }}
                  title={s.title}
                >
                  <span className="tdot" />
                  <span className="ritem-text">
                    <span className="ritem-title">{s.title}</span>
                    <span className="ritem-meta">
                      {relativeDay(s.updatedAt)}
                      {preview > 0 && ` · ${preview} cited`}
                    </span>
                  </span>
                </button>
                <button
                  className="ritem-del"
                  aria-label={`Delete ${s.title}`}
                  title="Delete conversation"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteSession(s.id)
                  }}
                >
                  <X width={11} height={11} />
                </button>
              </div>
            )
          })}
        </div>
      </div>

      <div className="rail-foot">
        <b>Index</b> {info ? `${info.count.toLocaleString()} recipes · ${info.dim}-d` : 'not loaded'}
        <br />
        <b>Embedder</b> {info ? info.model.replace('sentence-transformers/', '') : '—'}
        <br />
        <b>Retrieval</b> cosine · k={info?.k ?? '—'} · ≥{info?.min_similarity ?? '—'}
      </div>
    </aside>
  )
}
