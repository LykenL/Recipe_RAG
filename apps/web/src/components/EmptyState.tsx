import { Composer } from './Composer'
import { Basket, Clock, Dessert, Protein, Sparkle } from './icons'

export interface QuickStart {
  label: string
  hint: string
  prompt: string
  icon: 'clock' | 'protein' | 'dessert' | 'basket'
}

export const QUICK_STARTS: QuickStart[] = [
  {
    label: 'Quick dinner',
    hint: 'Under 20 min · ≤ 6 items',
    prompt:
      'Something for dinner tonight that takes under 20 minutes, uses 6 ingredients or fewer, and is at most 5 steps.',
    icon: 'clock',
  },
  {
    label: 'High protein',
    hint: '≥ 30 g protein, low fat',
    prompt: 'A high-protein, low-fat main dish, at least 30 g of protein per serving.',
    icon: 'protein',
  },
  {
    label: 'No-bake dessert',
    hint: 'No oven · 15 min',
    prompt: 'A dessert that needs no oven and no more than 15 minutes of hands-on work.',
    icon: 'dessert',
  },
  {
    label: 'Use my pantry',
    hint: 'Cook what you already have',
    prompt: 'What can I make right now using mainly the ingredients I already have?',
    icon: 'basket',
  },
]

function Icon({ name }: { name: QuickStart['icon'] }) {
  const style = { color: 'var(--terra)' }
  if (name === 'clock') return <Clock width={15} height={15} style={style} />
  if (name === 'protein') return <Protein width={15} height={15} style={style} />
  if (name === 'dessert') return <Dessert width={15} height={15} style={style} />
  if (name === 'basket') return <Basket width={15} height={15} style={style} />
  return <Sparkle width={15} height={15} style={style} />
}

interface Props {
  onSend: (text: string) => void
  onStop: () => void
  streaming: boolean
  tags: string[]
}

export function EmptyState({ onSend, onStop, streaming, tags }: Props) {
  return (
    <>
      <span className="eyebrow">
        <Sparkle width={12} height={12} />
        Agentic RAG · grounded in your cookbook
      </span>
      <h1 className="title">
        What are we <em>cooking</em>
        <br />
        tonight?
      </h1>
      <p className="lede">
        Ask about a recipe, a substitution, or what to make with the odds and ends in your fridge.
        Every answer is retrieved from the indexed recipes and cites the passages it used.
      </p>

      <Composer
        variant="hero"
        tags={tags}
        onSend={onSend}
        onStop={onStop}
        streaming={streaming}
        autoFocus
      />

      <div className="sugg-title">Quick starts</div>
      <div className="grid-4">
        {QUICK_STARTS.map((q) => (
          <button className="qcard" key={q.label} onClick={() => onSend(q.prompt)} disabled={streaming}>
            <div className="ic">
              <Icon name={q.icon} />
            </div>
            <h4>{q.label}</h4>
            <p>{q.hint}</p>
          </button>
        ))}
      </div>
    </>
  )
}
