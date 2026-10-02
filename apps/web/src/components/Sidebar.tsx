import { useState } from 'react'
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
  onNewChat: () => void
  history: string[]
  onPickHistory: (question: string) => void
  open: boolean
  onClose: () => void
}

export function Sidebar({
  settings,
  onChange,
  info,
  onNewChat,
  history,
  onPickHistory,
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
        <div className="rail-h">Recent</div>
        <div className="recent">
          {history.length === 0 ? (
            <div className="recent-empty">Questions you ask will show up here.</div>
          ) : (
            history.slice(-4).reverse().map((q, i) => (
              <button
                className={`ritem${i === 0 ? ' on' : ''}`}
                key={`${q}-${i}`}
                onClick={() => {
                  onPickHistory(q)
                  onClose()
                }}
                title={q}
              >
                <span className="tdot" />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {q}
                </span>
              </button>
            ))
          )}
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
