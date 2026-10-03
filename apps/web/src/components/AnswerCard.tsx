import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { DonePayload, Source } from '../lib/types'
import { Book, Check, Copy, Sparkle, Warn } from './icons'

interface Props {
  content: string
  sources: Source[]
  done?: DonePayload
  error?: string
  pending: boolean
  /** ingredients the user said they have, matched against the ingredient list */
  pantry?: string[]
}

const LIST_LINE = /^\s*([-*+]|\d+[.)])\s+/
/** Models like to emit a literal bullet glyph instead of markdown "- ". */
const BULLET_GLYPH = /^\s*[•·‣▪●]\s*/

/**
 * Make model output render predictably. Two real failure modes seen in
 * production, both of which are more reliably fixed here than by asking the
 * model to remember:
 *
 *   1. "**Ingredients**\n- item" — no blank line before a list, so CommonMark
 *      renders one paragraph ("Ingredients • 2 Lbs Chicken Wings").
 *   2. "• item" — a literal bullet glyph is not a list marker to CommonMark.
 *   3. "(blank line)" — narrating formatting instead of applying it.
 */
function normalizeMarkdown(md: string): string {
  const cleaned = md.replace(/\(blank lines?\)/gi, '').replace(/[ \t]+$/gm, '')
  const out: string[] = []

  for (const raw of cleaned.split('\n')) {
    const line = BULLET_GLYPH.test(raw) ? raw.replace(BULLET_GLYPH, '- ') : raw
    const prev = out[out.length - 1]
    if (LIST_LINE.test(line) && prev && prev.trim() !== '' && !LIST_LINE.test(prev)) {
      out.push('')
    }
    out.push(line)
  }
  return out.join('\n')
}

/**
 * The dish name is usually the first line, as a heading (`## X`), a bold line
 * (`**X**`), or — when the model ignores both — a bare short line immediately
 * followed by the ingredient list. Lifting it out lets the card set the title in
 * the display serif rather than as a bold paragraph.
 */
function splitTitle(markdown: string): { title?: string; body: string; improvised: boolean } {
  let body = markdown.trim()
  let improvised = false

  // creative mode prefixes invented recipes with this exact marker
  const marker = body.match(/^_Improvised[^_]*_\s*/i)
  if (marker) {
    improvised = true
    body = body.slice(marker[0].length)
  }

  const lines = body.split('\n')
  let i = 0
  while (i < lines.length && !lines[i].trim()) i += 1

  if (i < lines.length) {
    const line = lines[i].trim()
    const explicit =
      line.match(/^#{1,4}\s+(.+)$/)?.[1] ??
      line.match(/^\*\*(.+?)\*\*:?$/)?.[1] ??
      line.match(/^__(.+?)__:?$/)?.[1]

    // Bare title. The model often writes the dish name on its own line, then
    // "Based on **Dish**" on the next — which CommonMark merges into one
    // paragraph, so the check cannot be "the next line is a list".
    const SENTENCE_START = /^(here|based on|i |we |you |this|these|there|below|the following|sure|of course)\b/i
    let j = i + 1
    let listWithin3 = false
    for (let seen = 0; j < lines.length && seen < 3; j += 1) {
      const t = lines[j].trim()
      if (!t) continue
      seen += 1
      if (LIST_LINE.test(t)) {
        listWithin3 = true
        break
      }
    }
    const looksLikeName =
      line.length <= 60 &&
      line.split(/\s+/).length <= 6 &&
      !/[.:;!?]$/.test(line) &&
      !SENTENCE_START.test(line)
    const bare = !explicit && looksLikeName && listWithin3 ? line : undefined

    const candidate = explicit ?? bare
    if (candidate) {
      return {
        title: candidate.replace(/[*_`]/g, '').trim(),
        body: lines.slice(i + 1).join('\n').trim(),
        improvised,
      }
    }
  }
  return { body, improvised }
}

const FRACTIONS: Record<string, string> = {
  '1/2': '½', '1/4': '¼', '3/4': '¾', '1/3': '⅓', '2/3': '⅔',
  '1/8': '⅛', '3/8': '⅜', '5/8': '⅝', '7/8': '⅞',
}

/**
 * "1 1/2 cup" -> "1½ cup". Recipes are full of these and the slash form is a
 * typographic tell that nobody proofed the output.
 */
export function prettyFractions(md: string): string {
  let out = md
  for (const [k, v] of Object.entries(FRACTIONS)) {
    const esc = k.replace('/', '\\/')
    out = out.replace(new RegExp(`(\\d)\\s+${esc}(?![\\d/])`, 'g'), `$1${v}`)   // mixed number
    out = out.replace(new RegExp(`(?<![\\d/])${esc}(?![\\d/])`, 'g'), v)         // bare fraction
  }
  return out
}

/** True when `line` is a bullet item, i.e. an ingredient rather than a step. */
const BULLET_ITEM = /^\s*[-*+]\s+/

/** Which pantry item this line names, if any. Word-boundary matched so that
 *  "egg" does not match "eggplant". */
export function pantryHit(text: string, pantry: string[]): string | null {
  if (!pantry.length) return null
  const haystack = ` ${text.toLowerCase()} `
  for (const raw of pantry) {
    const key = raw.toLowerCase().trim()
    if (key.length < 3) continue
    const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    if (new RegExp(`[^a-z]${escaped}[^a-z]`).test(haystack)) return raw
  }
  return null
}

/** Flatten react-markdown's children back to plain text. */
function nodeText(node: ReactNode): string {
  if (node == null || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(nodeText).join('')
  const props = (node as { props?: { children?: ReactNode } }).props
  return props?.children ? nodeText(props.children) : ''
}

/** Set while rendering inside a <ul>, so only ingredient bullets get chips. */
const InBulletList = createContext(false)

const normaliseTitle = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

/**
 * Pick the photo of the dish the answer is actually about.
 *
 * The top-ranked source is not necessarily the one the model chose — it may
 * answer with the 2nd hit while the 1st stays the best-scoring. Using
 * sources[0] blindly put a photo of Kentucky Fried Chicken on a Piri-piri
 * recipe. Showing no photo is better than showing the wrong dish.
 */
function heroImage(title: string | undefined, sources: Source[]): string {
  const withImage = sources.filter((s) => s.image)
  if (withImage.length === 0) return ''
  if (!title) return withImage[0].image ?? ''

  const want = normaliseTitle(title)
  const exact = withImage.find((s) => normaliseTitle(s.title) === want)
  if (exact) return exact.image ?? ''

  // tolerate "Recipe (Pollo a la Naranja)" style suffixes in either direction
  const partial = withImage.find((s) => {
    const got = normaliseTitle(s.title)
    return got.length >= 6 && (want.includes(got) || got.includes(want))
  })
  return partial?.image ?? ''
}

export function AnswerCard({
  content,
  sources,
  done,
  error,
  pending,
  pantry = [],
}: Props) {
  const [copied, setCopied] = useState(false)
  const { title, body, improvised } = splitTitle(normalizeMarkdown(content))
  const rendered = prettyFractions(body)

  // Only bullets get pantry chips. Numbered lists are method steps, where
  // "add the chicken" would otherwise look like a pantry claim.
  const mdComponents = useMemo(
    () => ({
      ul: ({ children }: { children?: ReactNode }) => (
        <ul>
          <InBulletList.Provider value={true}>{children}</InBulletList.Provider>
        </ul>
      ),
      li: ({ children }: { children?: ReactNode }) => {
        const inBullets = useContext(InBulletList)
        const hit = inBullets ? pantryHit(nodeText(children), pantry) : null
        return (
          <li>
            {children}
            {hit && <span className="ing-have">in pantry</span>}
          </li>
        )
      },
    }),
    [pantry],
  )

  const haveCount = useMemo(() => {
    if (!pantry.length) return 0
    return rendered
      .split('\n')
      .filter((l) => BULLET_ITEM.test(l) && pantryHit(l, pantry))
      .length
  }, [rendered, pantry])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard can be blocked; silently ignore */
    }
  }

  if ((error || !content.trim()) && !pending) {
    // An empty answer with real sources is worse than an error: the footer would
    // claim "grounded in N sources" over a blank card. Say what happened instead.
    return (
      <div className="answer">
        <div className="ans-body">
          <div className="copy-error" style={{ margin: 0 }}>
            <Warn width={16} height={16} style={{ flex: 'none' }} />
            <span>
              {error ??
                'The model returned no answer this time. This usually means it used its whole budget on internal reasoning — ask again, or rephrase the question.'}
            </span>
          </div>
        </div>
      </div>
    )
  }

  const citationLabel =
    done && done.citations > 0
      ? `Grounded in ${done.citations} source${done.citations === 1 ? '' : 's'} · every claim resolves to a citation`
      : done
        ? 'No cookbook match — answered without sources'
        : ''

  // Photo of the dish this answer is actually about (not simply the top hit).
  const hero = heroImage(title, sources)

  return (
    <div className="answer">
      <div
        className={`ans-head${hero ? ' on-photo' : ''}`}
        style={hero ? { backgroundImage: `url("${hero}")` } : undefined}
      >
        {hero && <div className="ans-hero-scrim" />}
        <div className="ans-head-inner">
          {improvised && (
            <span className="badge-improvised">
              <Sparkle width={12} height={12} /> Improvised — not from your cookbook
            </span>
          )}
          {title && <h2>{title}</h2>}
          {done && (
            <p className="ans-sub">
              {done.searches} cookbook search{done.searches === 1 ? '' : 'es'} ·{' '}
              {(done.elapsed_ms / 1000).toFixed(1)}s
            </p>
          )}
        </div>
      </div>

      <div className="ans-body">
        <div className="answer-md">
          <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{rendered}</Markdown>
          {pending && <span className="caret" />}
        </div>
      </div>

      {!pending && (
        <div className="ans-foot">
          <span>{citationLabel}</span>
          {haveCount > 0 && (
            <span className="act" style={{ background: 'var(--sage-soft)', borderColor: 'var(--sage-line)', color: '#2E6240' }}>
              {haveCount} in your pantry
            </span>
          )}
          {sources.length > 0 && (
            <span className="act" title="Sources are listed in the panel">
              <Book width={12} height={12} /> {sources.length} sources
            </span>
          )}
          <span className="act" onClick={copy} role="button" tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && copy()}>
            {copied ? <Check width={12} height={12} /> : <Copy width={12} height={12} />}
            {copied ? 'Copied' : 'Copy'}
          </span>
        </div>
      )}
    </div>
  )
}
